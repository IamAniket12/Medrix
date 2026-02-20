"""Embeddings service for RAG-based retrieval using Google Vertex AI."""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel

from ..models import (
    Document,
    DocumentEmbedding,
    TimelineEvent,
    TimelineEventEmbedding,
    ClinicalEntityEmbedding,
    ClinicalCondition,
    ClinicalMedication,
    ClinicalLabResult,
    ClinicalProcedure,
)
from ..core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Service for generating and managing vector embeddings for RAG."""

    def __init__(self):
        """Initialize the embeddings service (lazy initialization)."""
        self.model = None
        self.embedding_dimension = 768
        self._initialized = False

    def _ensure_initialized(self):
        """Ensure the service is initialized with Vertex AI."""
        if self._initialized:
            return

        try:
            # Load credentials if specified
            credentials = None
            if settings.google_application_credentials:
                from google.oauth2 import service_account

                credentials = service_account.Credentials.from_service_account_file(
                    settings.google_application_credentials
                )

            # Initialize Vertex AI
            aiplatform.init(
                project=settings.google_cloud_project,
                location=settings.vertex_ai_location,
                credentials=credentials,
            )

            # Use Google's text-embedding-004 model (768 dimensions)
            self.model = TextEmbeddingModel.from_pretrained("text-embedding-004")
            self._initialized = True
            logger.info("Embeddings service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize embeddings service: {str(e)}")
            logger.warning("Embeddings service will operate in fallback mode")
            # Don't raise - allow app to start but embeddings won't work
            self._initialized = False

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector (768 dimensions)
        """
        self._ensure_initialized()

        if not self._initialized:
            # Fallback: return zero vector if not initialized
            logger.warning("Embeddings service not initialized, returning zero vector")
            return [0.0] * self.embedding_dimension

        try:
            embeddings = self.model.get_embeddings([text])
            return embeddings[0].values
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        self._ensure_initialized()

        if not self._initialized:
            # Fallback: return zero vectors if not initialized
            logger.warning("Embeddings service not initialized, returning zero vectors")
            return [[0.0] * self.embedding_dimension for _ in texts]

        try:
            embeddings = self.model.get_embeddings(texts)
            return [emb.values for emb in embeddings]
        except Exception as e:
            logger.error(f"Error generating embeddings batch: {str(e)}")
            raise

    def chunk_document_text(
        self, text: str, chunk_size: int = 1000, overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """
        DEPRECATED: Split document text into overlapping chunks for better retrieval.

        This method is no longer used. We now use Agent 3's search-optimized summaries
        instead of raw text chunking for better semantic search quality.

        Args:
            text: Full document text
            chunk_size: Maximum characters per chunk
            overlap: Number of characters to overlap between chunks

        Returns:
            List of chunks with metadata
        """
        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk_text.rfind(".")
                last_newline = chunk_text.rfind("\n")
                break_point = max(last_period, last_newline)
                if (
                    break_point > chunk_size * 0.5
                ):  # Only break if we're at least halfway
                    end = start + break_point + 1
                    chunk_text = text[start:end]

            chunks.append(
                {
                    "text": chunk_text.strip(),
                    "chunk_index": chunk_index,
                    "start": start,
                    "end": end,
                }
            )

            start = end - overlap  # Overlap for context
            chunk_index += 1

        return chunks

    def create_document_embeddings(
        self,
        db: Session,
        document: Document,
        summaries: Dict[str, Any],
        clinical_data: Dict[str, Any],
    ) -> List[DocumentEmbedding]:
        """
        Create SMART embeddings using Agent 3's search-optimized summaries.
        No more raw text chunking - we use AI-generated summaries for better semantic search.

        Args:
            db: Database session
            document: Document object
            summaries: Agent 3's output (includes search_optimized_summary)
            clinical_data: Agent 2's extracted data

        Returns:
            List of created DocumentEmbedding objects
        """
        try:
            document_embeddings = []

            # 1. Main search-optimized summary (highest priority)
            search_summary = summaries.get("search_optimized_summary", "")
            if search_summary:
                # Enrich with clinical data for completeness
                meds = [
                    m.get("name", "") for m in clinical_data.get("medications", [])[:10]
                ]
                conditions = [
                    c.get("name", "") for c in clinical_data.get("conditions", [])[:10]
                ]

                enriched_summary = f"""{search_summary}

Medications: {', '.join(meds) if meds else 'None documented'}
Conditions: {', '.join(conditions) if conditions else 'None documented'}"""

                embedding_vector = self.generate_embedding(enriched_summary)
                doc_embedding = DocumentEmbedding(
                    document_id=document.id,
                    user_id=document.user_id,
                    chunk_text=enriched_summary,
                    chunk_index=0,  # Main summary
                    embedding=embedding_vector,
                    document_type=document.document_type,
                    document_date=document.document_date,
                )
                db.add(doc_embedding)
                document_embeddings.append(doc_embedding)

            # 2. Key findings (granular search)
            key_findings = summaries.get("detailed_summary", {}).get("key_findings", [])
            for idx, finding in enumerate(key_findings[:5], start=1):  # Limit to top 5
                if finding and len(finding.strip()) > 10:
                    embedding_vector = self.generate_embedding(finding)
                    finding_embedding = DocumentEmbedding(
                        document_id=document.id,
                        user_id=document.user_id,
                        chunk_text=f"Key Finding: {finding}",
                        chunk_index=idx,
                        embedding=embedding_vector,
                        document_type=document.document_type,
                        document_date=document.document_date,
                    )
                    db.add(finding_embedding)
                    document_embeddings.append(finding_embedding)

            db.commit()
            logger.info(
                f"Created {len(document_embeddings)} smart embeddings for document {document.id}"
            )
            return document_embeddings

        except Exception as e:
            logger.error(f"Error creating document embeddings: {str(e)}")
            db.rollback()
            raise

    def create_timeline_event_embedding(
        self, db: Session, event: TimelineEvent, search_summary: Optional[str] = None
    ) -> TimelineEventEmbedding:
        """
        Create embedding for a timeline event using search-optimized summary.

        Args:
            db: Database session
            event: TimelineEvent object
            search_summary: Search-optimized summary from Agent 3 (preferred)

        Returns:
            Created TimelineEventEmbedding object
        """
        try:
            # Use Agent 3's search_summary if provided, otherwise create basic summary
            if search_summary:
                event_summary = search_summary
            else:
                # Fallback: Create enhanced summary with synonyms
                event_type_map = {
                    "diagnosis": "diagnosis diagnosed condition identified",
                    "medication_started": "medication started prescribed began initiated",
                    "medication_stopped": "medication stopped discontinued ceased ended",
                    "lab_result": "lab result laboratory test blood work analysis",
                    "procedure": "procedure operation surgery intervention",
                    "visit": "visit appointment consultation check-up",
                    "hospitalization": "hospitalization admitted hospital admission inpatient",
                }
                event_type_expanded = event_type_map.get(
                    event.event_type, event.event_type
                )

                event_summary = f"""{event_type_expanded}: {event.event_title}
{event.event_description or ''}
Date: {event.event_date.strftime('%Y-%m-%d') if event.event_date else 'Unknown'}
Provider: {event.provider or ''} Facility: {event.facility or ''}
Importance: {event.importance or 'medium'}""".strip()

            # Generate embedding
            embedding_vector = self.generate_embedding(event_summary)

            # Create TimelineEventEmbedding record
            event_embedding = TimelineEventEmbedding(
                event_id=event.id,
                user_id=event.user_id,
                event_summary=event_summary,
                embedding=embedding_vector,
                event_type=event.event_type,
                event_date=event.event_date,
                importance=event.importance,
            )
            db.add(event_embedding)
            db.commit()

            logger.info(f"Created embedding for timeline event {event.id}")
            return event_embedding

        except Exception as e:
            logger.error(f"Error creating timeline event embedding: {str(e)}")
            db.rollback()
            raise

    def create_clinical_entity_embedding(
        self,
        db: Session,
        user_id: str,
        entity_type: str,
        entity_id: int,
        entity_name: str,
        entity_data: Dict[str, Any],
    ) -> ClinicalEntityEmbedding:
        """
        Create embedding for a clinical entity (medication, condition, lab, procedure).

        Args:
            db: Database session
            user_id: User ID
            entity_type: Type of entity (medication, condition, lab_result, procedure)
            entity_id: ID of the entity
            entity_name: Name of the entity
            entity_data: Dictionary with entity details

        Returns:
            Created ClinicalEntityEmbedding object
        """
        try:
            # Create SEARCH-OPTIMIZED summary with synonyms and expanded terminology
            if entity_type == "medication":
                generic = entity_data.get("generic_name", "")
                route = entity_data.get("route", "oral")

                entity_summary = f"""Medication drug pharmaceutical: {entity_name} {generic if generic else ''}
Dosage strength: {entity_data.get('dosage', '')} {route} route
Frequency schedule: {entity_data.get('frequency', 'as prescribed')}
Started: {entity_data.get('start_date', 'unknown')}
Status: {entity_data.get('status', 'active')} currently taking prescribed
Instructions: {entity_data.get('instructions', '')}""".strip()

            elif entity_type == "condition":
                icd10 = entity_data.get("icd10_code", "")
                body_site = entity_data.get("body_site", "")

                entity_summary = f"""Condition diagnosis disease illness: {entity_name} {icd10 if icd10 else ''}
Status: {entity_data.get('status', 'active')} current ongoing
Severity: {entity_data.get('severity', 'moderate')} {body_site if body_site else ''}
Diagnosed identified: {entity_data.get('diagnosed_date', 'unknown')}
Medical condition health issue""".strip()

            elif entity_type == "lab_result":
                loinc = entity_data.get("loinc_code", "")
                abnormal = (
                    "abnormal elevated high low"
                    if entity_data.get("is_abnormal")
                    else "normal"
                )

                entity_summary = f"""Lab test laboratory blood work analysis: {entity_name} {loinc if loinc else ''}
Result value measurement: {entity_data.get('value', '')} {entity_data.get('unit', '')}
Reference range normal: {entity_data.get('reference_range', '')}
Status: {abnormal}
Test date: {entity_data.get('test_date', 'unknown')}
Laboratory panel screening""".strip()

            elif entity_type == "procedure":
                cpt = entity_data.get("cpt_code", "")
                outcome = entity_data.get("outcome", "completed")

                entity_summary = f"""Procedure operation surgery intervention: {entity_name} {cpt if cpt else ''}
Performed: {entity_data.get('performed_date', 'unknown')}
Provider doctor surgeon: {entity_data.get('provider', '')}
Facility hospital clinic: {entity_data.get('facility', '')}
Outcome result: {outcome} successful
Medical procedure surgical intervention""".strip()
            else:
                entity_summary = f"{entity_type}: {entity_name}"

            # Generate embedding
            embedding_vector = self.generate_embedding(entity_summary)

            # Create ClinicalEntityEmbedding record
            entity_embedding = ClinicalEntityEmbedding(
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                entity_summary=entity_summary,
                embedding=embedding_vector,
                first_seen=entity_data.get("first_seen"),
                last_seen=entity_data.get("last_seen"),
            )
            db.add(entity_embedding)
            db.commit()

            logger.info(f"Created embedding for {entity_type} {entity_id}")
            return entity_embedding

        except Exception as e:
            logger.error(f"Error creating clinical entity embedding: {str(e)}")
            db.rollback()
            raise

    def search_similar_documents(
        self,
        db: Session,
        user_id: str,
        query: str,
        limit: int = 10,
        document_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar document chunks using vector similarity.

        Args:
            db: Database session
            user_id: User ID to filter by
            query: Search query text
            limit: Maximum number of results
            document_type: Optional document type filter

        Returns:
            List of similar document chunks with metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query)

            # Build query with vector similarity (cosine distance)
            query_filter = f"de.user_id = '{user_id}' AND de.deleted_at IS NULL"
            if document_type:
                query_filter += f" AND de.document_type = '{document_type}'"

            # Use pgvector's <=> operator for cosine distance
            sql = text(
                f"""
                SELECT 
                    de.id,
                    de.document_id,
                    de.chunk_text,
                    de.chunk_index,
                    de.document_type,
                    de.document_date,
                    d.filename,
                    d.original_name,
                    (de.embedding <=> CAST(:query_embedding AS vector)) as distance
                FROM document_embeddings de
                JOIN documents d ON de.document_id = d.id
                WHERE {query_filter}
                ORDER BY de.embedding <=> CAST(:query_embedding AS vector)
                LIMIT :limit
            """
            )

            result = db.execute(
                sql, {"query_embedding": query_embedding, "limit": limit}
            )

            results = []
            for row in result:
                results.append(
                    {
                        "embedding_id": row[0],
                        "document_id": row[1],
                        "chunk_text": row[2],
                        "chunk_index": row[3],
                        "document_type": row[4],
                        "document_date": row[5],
                        "filename": row[6],
                        "original_name": row[7],
                        "similarity_score": 1
                        - row[8],  # Convert distance to similarity
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Error searching similar documents: {str(e)}")
            raise

    def search_similar_timeline_events(
        self,
        db: Session,
        user_id: str,
        query: str,
        limit: int = 10,
        event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar timeline events using vector similarity.

        Args:
            db: Database session
            user_id: User ID to filter by
            query: Search query text
            limit: Maximum number of results
            event_type: Optional event type filter

        Returns:
            List of similar timeline events with metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query)

            # Build query
            query_filter = f"tee.user_id = '{user_id}' AND tee.deleted_at IS NULL"
            if event_type:
                query_filter += f" AND tee.event_type = '{event_type}'"

            sql = text(
                f"""
                SELECT 
                    tee.id,
                    tee.event_id,
                    tee.event_summary,
                    tee.event_type,
                    tee.event_date,
                    tee.importance,
                    te.event_title,
                    te.event_description,
                    (tee.embedding <=> CAST(:query_embedding AS vector)) as distance
                FROM timeline_event_embeddings tee
                JOIN timeline_events te ON tee.event_id = te.id
                WHERE {query_filter}
                ORDER BY tee.embedding <=> CAST(:query_embedding AS vector)
                LIMIT :limit
            """
            )

            result = db.execute(
                sql, {"query_embedding": query_embedding, "limit": limit}
            )

            results = []
            for row in result:
                results.append(
                    {
                        "embedding_id": row[0],
                        "event_id": row[1],
                        "event_summary": row[2],
                        "event_type": row[3],
                        "event_date": row[4],
                        "importance": row[5],
                        "event_title": row[6],
                        "event_description": row[7],
                        "similarity_score": 1 - row[8],
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Error searching similar timeline events: {str(e)}")
            raise

    def get_patient_context(
        self,
        db: Session,
        user_id: str,
        current_document_date: Optional[datetime] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Get comprehensive patient context for Agent 5 (Context Agent).
        Retrieves relevant historical data before processing new document.

        Args:
            db: Database session
            user_id: User ID
            current_document_date: Date of document being processed (to filter historical data)
            limit: Maximum items per category

        Returns:
            Dictionary with patient context including medications, conditions, recent events
        """
        try:
            # Query for active medications
            medications_query = db.query(ClinicalMedication).filter(
                ClinicalMedication.user_id == user_id,
                ClinicalMedication.deleted_at.is_(None),
                ClinicalMedication.is_active == True,
            )
            if current_document_date:
                medications_query = medications_query.filter(
                    ClinicalMedication.start_date <= current_document_date
                )
            medications = medications_query.limit(limit).all()

            # Query for active conditions
            conditions_query = db.query(ClinicalCondition).filter(
                ClinicalCondition.user_id == user_id,
                ClinicalCondition.deleted_at.is_(None),
                ClinicalCondition.status.in_(["active", "chronic"]),
            )
            if current_document_date:
                conditions_query = conditions_query.filter(
                    ClinicalCondition.diagnosed_date <= current_document_date
                )
            conditions = conditions_query.limit(limit).all()

            # Query for recent timeline events
            events_query = db.query(TimelineEvent).filter(
                TimelineEvent.user_id == user_id, TimelineEvent.deleted_at.is_(None)
            )
            if current_document_date:
                events_query = events_query.filter(
                    TimelineEvent.event_date <= current_document_date
                )
            events = (
                events_query.order_by(TimelineEvent.event_date.desc())
                .limit(limit)
                .all()
            )

            # Build context dictionary
            context = {
                "user_id": user_id,
                "active_medications": [
                    {
                        "name": med.name,
                        "dosage": med.dosage,
                        "frequency": med.frequency,
                        "start_date": (
                            med.start_date.isoformat() if med.start_date else None
                        ),
                        "prescriber": med.prescriber,
                    }
                    for med in medications
                ],
                "active_conditions": [
                    {
                        "name": cond.name,
                        "status": cond.status,
                        "severity": cond.severity,
                        "diagnosed_date": (
                            cond.diagnosed_date.isoformat()
                            if cond.diagnosed_date
                            else None
                        ),
                    }
                    for cond in conditions
                ],
                "recent_events": [
                    {
                        "event_type": event.event_type,
                        "event_title": event.event_title,
                        "event_date": (
                            event.event_date.isoformat() if event.event_date else None
                        ),
                        "importance": event.importance,
                    }
                    for event in events
                ],
                "summary": {
                    "total_active_medications": len(medications),
                    "total_active_conditions": len(conditions),
                    "total_recent_events": len(events),
                },
            }

            return context

        except Exception as e:
            logger.error(f"Error getting patient context: {str(e)}")
            raise

    def search_similar_clinical_entities(
        self,
        db: Session,
        user_id: str,
        query: str,
        limit: int = 10,
        entity_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar clinical entities using vector similarity.

        Args:
            db: Database session
            user_id: User ID to filter by
            query: Search query text
            limit: Maximum number of results
            entity_type: Optional entity type filter (medication, condition, lab_result, procedure)

        Returns:
            List of similar clinical entities with metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query)

            # Build query
            query_filter = f"cee.user_id = '{user_id}' AND cee.deleted_at IS NULL"
            if entity_type:
                query_filter += f" AND cee.entity_type = '{entity_type}'"

            sql = text(
                f"""
                SELECT 
                    cee.id,
                    cee.entity_id,
                    cee.entity_type,
                    cee.entity_name,
                    cee.entity_summary,
                    cee.first_seen,
                    cee.last_seen,
                    (cee.embedding <=> CAST(:query_embedding AS vector)) as distance
                FROM clinical_entity_embeddings cee
                WHERE {query_filter}
                ORDER BY cee.embedding <=> CAST(:query_embedding AS vector)
                LIMIT :limit
            """
            )

            result = db.execute(
                sql, {"query_embedding": query_embedding, "limit": limit}
            )

            results = []
            for row in result:
                results.append(
                    {
                        "embedding_id": row[0],
                        "entity_id": row[1],
                        "entity_type": row[2],
                        "entity_name": row[3],
                        "entity_summary": row[4],
                        "first_seen": row[5],
                        "last_seen": row[6],
                        "similarity_score": 1
                        - row[7],  # Convert distance to similarity
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Error searching similar clinical entities: {str(e)}")
            raise


# Singleton instance
embeddings_service = EmbeddingsService()
