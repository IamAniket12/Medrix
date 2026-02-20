# Medrix - AI-Powered Medical History Management Platform

## Project Overview
Medrix is a medical history management platform with AI-powered document extraction, timeline visualization, RAG search, and medical ID card generation.

## Tech Stack
- **Frontend**: Next.js 14 with TypeScript and App Router
- **Styling**: Tailwind CSS, Material-UI, Shadcn/ui
- **Database**: PostgreSQL with Prisma ORM (hosted on Railway)
- **File Storage**: Local storage (development), GCP (production)
- **AI/ML**: MedGemma for document extraction, RAG for search
- **Authentication**: Skipped for now (Phase 2)

## Project Structure
- `/app` - Next.js App Router pages and API routes
- `/components` - React components
- `/lib` - Utility functions and configurations
- `/types` - TypeScript type definitions
- `/prisma` - Database schema and migrations
- `/public` - Static assets
- `/uploads` - Local file storage (development only)

## Development Guidelines
- Use TypeScript for all files
- Follow React best practices
- Use Prisma for database operations
- Keep components modular and reusable
- Document complex logic with comments

## Current Phase: Phase 1 - Core Foundation
Focus on authentication, document upload, and basic UI.
