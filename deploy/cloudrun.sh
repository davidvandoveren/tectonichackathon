#!/usr/bin/env bash
# Deploy to Google Cloud Run straight from source (Cloud Build builds the Dockerfile).
# Usage: PROJECT_ID=my-project ./deploy/cloudrun.sh
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-europe-west1}"
SERVICE="${SERVICE:-tectonichackathon}"
SECRET="${SECRET:-demo-password}"

gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com

# The demo password lives in Secret Manager, never in the repo or in plain env vars.
if ! gcloud secrets describe "$SECRET" >/dev/null 2>&1; then
  read -r -s -p "Demo password for the personas (min 8 chars): " DEMO_PASSWORD; echo
  printf '%s' "$DEMO_PASSWORD" | gcloud secrets create "$SECRET" --data-file=-
fi
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
gcloud secrets add-iam-policy-binding "$SECRET" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role=roles/secretmanager.secretAccessor >/dev/null

# max-instances=1: demo data and sessions are in memory (see README "Known limitations").
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --max-instances 1 \
  --memory 512Mi \
  --set-env-vars APP_ENV=production \
  --set-secrets "DEMO_PASSWORD=${SECRET}:latest"
