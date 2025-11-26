🏥 Rehab App — Ingestion Layer
Archived Project — Awaiting pVerify Access & AI Budget

This repository contains the ingestion and enrichment pipeline for the Rehab App — a platform designed to help patients search for, evaluate, and get approved for rehabilitation centers across the United States.

The ingestion layer is responsible for:

Identifying legitimate rehab organizations (via NPI registry + taxonomy filtering)

Extracting authoritative data from provider websites

Structuring the data into a normalized format for the Rehab App API

This monorepo is built with uv
and consists of multiple Python packages that work together to gather, enrich, and prepare rehab organization data.

📦 Monorepo Structure (UV Workspace)
[tool.uv.workspace]
members = [
"packages/common",
"packages/npi-puller",
"packages/enricher",
]

Each package plays a distinct role in the ingestion pipeline.

📁 Packages Overview

1. packages/common

Shared utilities and SDKs used across the ingestion system.

Key features:

Ariadne GraphQL client codegen for communicating with the Rehab App backend

The backend is a NestJS GraphQL API

Codegen produces a strongly typed client for mutations, queries, and input models

Shared schemas, helpers, and domain types used in the enrichment pipeline

Reusable error handling, async utilities, and configuration helpers

This package acts as the foundation layer for cross-package code reuse.

2. packages/npi-puller

Async ingestion pipeline for gathering official rehab organizations.

Capabilities include:

Fetching data from the NPI Registry API

Processing the monthly NPPES downloadable provider files

Filtering providers using rehabilitation-related taxonomy codes

Identifying facilities that are:

Legitimate health organizations

Operating in the addiction treatment / rehabilitation domain

Registered with official NPI numbers

Produces a dataset of ~1,200 rehab organizations across the U.S.

This serves as the ground-truth list of real rehab centers for the entire system.

3. packages/enricher

The enrichment pipeline powered by the OpenAI Agents SDK.

Purpose:

Take the base NPI data & official website

Crawl the organization’s website

Extract detailed structured information

Highlights:

Uses the OpenAI Agents SDK with:

Dynamic instructions

Multi-agent orchestration

Structured Pydantic outputs

Tool-calling (e.g., web crawler → markdown converter)

Builds rich metadata:

Organization details (name, legal entity, description, phones)

Programs & services (detox, MAT, inpatient, outpatient)

Admissions & insurance payers

Campuses & facility details

Parent company information

Operates through:

Rehab Confirmation Agent → verifies official website

Sitemap Categorization Agent → organizes URLs into buckets

Per-Category Enrichment Agents → extract structured data using markdown

Produces a fully enriched, normalized JSON dataset ready for the Rehab App API

This package is the heart of the intelligence layer — transforming raw web data into application-ready structured entities.

🗂️ Data Flow Overview

1. NPI Puller
   NPI Registry + Monthly NPPES Files
   ↓
   Taxonomy-Based Filtering
   ↓
   1200+ Rehab Organizations (seed dataset)

2. Enricher
   NPI Org → Confirm Official Website → Fetch Sitemap
   ↓
   Categorize URLs → Extract Markdown via Async Crawler
   ↓
   OpenAI Multi-Agent Enrichment Pipeline
   ↓
   Final Structured Output (JSON)

3. Output

Data is intended to be submitted to the Rehab App NestJS GraphQL API via the generated SDK in packages/common.

📉 Project Status — Archived

This project is currently paused due to:

Pending access to pVerify API, which is required for insurance verification workflows

Cost constraints for running large-scale enrichment using AI model credits

Anticipated redesign once higher-quality insurance + eligibility data becomes available

When resumed, the ingestion pipeline will integrate:

Verified insurance eligibility (pVerify)

Organizational credential validation

More efficient enrichment workflows (smarter batching, lower-cost models)

📌 Notes

This repository is a snapshot of the system before pausing development

It showcases an advanced ingestion layer integrating NPI data, web crawling, and LLM-based enrichment

Future versions will optimize extraction pipelines, refine schemas, and integrate insurance verification services

🛑 Archival Summary

This repo is archived not because it's deprecated, but because:

The pipeline works

But requires external data sources (pVerify) and model budget to scale

Will be resumed in a future iteration of the Rehab App project
