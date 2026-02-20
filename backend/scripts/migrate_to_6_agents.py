"""
Database migration script to add vector embeddings support.

This script:
1. Enables pgvector extension
2. Creates embedding tables (document_embeddings, timeline_event_embeddings, clinical_entity_embeddings)
3. Creates vector indexes for fast similarity search
4. Migrates existing data (creates embeddings for existing documents and events)

Run this after upgrading to the 6-agent system.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from src.core.database import SessionLocal, engine
from src.models import Base, Document, TimelineEvent
from src.services.embeddings_service import embeddings_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def enable_pgvector():
    """Enable the pgvector extension in PostgreSQL."""
    logger.info("Enabling pgvector extension...")

    with engine.connect() as conn:
        try:
            # Check if extension exists
            result = conn.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                )
            )
            exists = result.scalar()

            if not exists:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
                logger.info("✓ pgvector extension enabled")
            else:
                logger.info("✓ pgvector extension already enabled")

        except Exception as e:
            logger.error(f"Failed to enable pgvector: {e}")
            logger.info("Please run manually: CREATE EXTENSION vector;")
            raise


def create_tables():
    """Create all tables including embedding tables."""
    logger.info("Creating database tables...")

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ All tables created successfully")

    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise


def migrate_existing_data():
    """Create embeddings for existing documents and timeline events."""
    logger.info("\n" + "=" * 60)
    logger.info("MIGRATING EXISTING DATA TO VECTOR EMBEDDINGS")
    logger.info("=" * 60 + "\n")

    db = SessionLocal()

    try:
        # Get all documents (Document model doesn't have deleted_at)
        documents = db.query(Document).all()

        logger.info(f"Found {len(documents)} documents to process")

        for i, document in enumerate(documents, 1):
            try:
                logger.info(
                    f"\n[{i}/{len(documents)}] Processing document: {document.filename}"
                )

                # Check if embeddings already exist
                from src.models import DocumentEmbedding

                existing = (
                    db.query(DocumentEmbedding)
                    .filter(DocumentEmbedding.document_id == document.id)
                    .first()
                )

                if existing:
                    logger.info("  ⏭️  Embeddings already exist, skipping")
                    continue

                # Get document summary/text
                # NOTE: This migration script uses old embedding approach (raw text)
                # For best results, re-upload documents after smart embeddings upgrade
                if document.summary and hasattr(document.summary, "brief_summary"):
                    document_text = document.summary.brief_summary
                else:
                    document_text = (
                        f"Document: {document.filename} Type: {document.document_type}"
                    )

                # DEPRECATED: Uses old signature with raw text
                # TODO: Update to use summaries + clinical_data once available
                try:
                    # Try new signature first (if summaries available)
                    if hasattr(document, "extracted_data") and document.extracted_data:
                        summaries = document.extracted_data.get("summaries", {})
                        clinical_data = document.extracted_data.get("clinical_data", {})
                        if summaries:
                            doc_embeddings = (
                                embeddings_service.create_document_embeddings(
                                    db=db,
                                    document=document,
                                    summaries=summaries,
                                    clinical_data=clinical_data,
                                )
                            )
                        else:
                            raise ValueError("No summaries available, using fallback")
                    else:
                        raise ValueError("No extracted_data, using fallback")
                except:
                    # Fallback: Skip embedding creation for old documents
                    logger.warning(
                        f"  ⚠️  Skipping embeddings for document {document.id} (no Agent 3 summaries available)"
                    )
                    continue
                logger.info(f"  ✓ Created {len(doc_embeddings)} document embeddings")

            except Exception as e:
                logger.error(
                    f"  ❌ Failed to create embeddings for document {document.id}: {e}"
                )
                continue

        # Get all timeline events that don't have embeddings yet
        timeline_events = (
            db.query(TimelineEvent).filter(TimelineEvent.deleted_at.is_(None)).all()
        )

        logger.info(f"\nFound {len(timeline_events)} timeline events to process")

        for i, event in enumerate(timeline_events, 1):
            try:
                logger.info(
                    f"\n[{i}/{len(timeline_events)}] Processing event: {event.event_title}"
                )

                # Check if embedding already exists
                from src.models import TimelineEventEmbedding

                existing = (
                    db.query(TimelineEventEmbedding)
                    .filter(TimelineEventEmbedding.event_id == event.id)
                    .first()
                )

                if existing:
                    logger.info("  ⏭️  Embedding already exists, skipping")
                    continue

                # Create timeline event embedding
                event_embedding = embeddings_service.create_timeline_event_embedding(
                    db=db, event=event
                )
                logger.info(f"  ✓ Created timeline event embedding")

            except Exception as e:
                logger.error(
                    f"  ❌ Failed to create embedding for event {event.id}: {e}"
                )
                continue

        logger.info("\n" + "=" * 60)
        logger.info("✅ MIGRATION COMPLETE")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

    finally:
        db.close()


def create_vector_indexes():
    """Create IVFFlat indexes for fast vector similarity search."""
    logger.info("\nCreating vector indexes...")

    with engine.connect() as conn:
        try:
            # Create IVFFlat index for document embeddings
            # Using lists=100 for datasets with 1000-100000 rows
            conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_document_embeddings_vector 
                ON document_embeddings 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """
                )
            )
            logger.info("✓ Document embeddings vector index created")

            # Create IVFFlat index for timeline event embeddings
            conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_timeline_embeddings_vector 
                ON timeline_event_embeddings 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """
                )
            )
            logger.info("✓ Timeline event embeddings vector index created")

            # Create IVFFlat index for clinical entity embeddings
            conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_clinical_embeddings_vector 
                ON clinical_entity_embeddings 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """
                )
            )
            logger.info("✓ Clinical entity embeddings vector index created")

            conn.commit()
            logger.info("✓ All vector indexes created successfully")

        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            # Non-critical, can continue


def main():
    """Main migration function."""
    print("\n" + "=" * 60)
    print("MEDRIX 6-AGENT SYSTEM - VECTOR EMBEDDINGS MIGRATION")
    print("=" * 60 + "\n")

    try:
        # Step 1: Enable pgvector
        enable_pgvector()

        # Step 2: Create tables
        create_tables()

        # Step 3: Create vector indexes
        create_vector_indexes()

        # Step 4: Migrate existing data
        migrate_existing_data()

        print("\n" + "=" * 60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nYour database is now ready for the 6-agent system with RAG!")
        print("You can now:")
        print("  1. Upload documents and get RAG-based context")
        print("  2. Use semantic search across documents and timeline")
        print("  3. Get relationship mapping between clinical entities")
        print("\n")

    except Exception as e:
        print(f"\n❌ MIGRATION FAILED: {e}")
        print("\nPlease check the error messages above and fix any issues.")
        sys.exit(1)


if __name__ == "__main__":
    main()
