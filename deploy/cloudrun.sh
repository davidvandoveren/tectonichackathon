#!/usr/bin/env bash
# Deploy to Google Cloud Run straight from source (Cloud Build builds the Dockerfile).
# Usage: PROJECT_ID=my-project ./deploy/cloudrun.sh
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-europe-west1}"
SERVICE="${SERVICE:-tectonichackathon}"
SECRET="${SECRET:-demo-password}"
# The identity the service runs as (6-30 chars, lowercase letters, digits, dashes).
RUNTIME_SA="${RUNTIME_SA:-${SERVICE}-run}"
SA_EMAIL="${RUNTIME_SA}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com iam.googleapis.com

# Least privilege: the service runs as its own service account with no project roles at all, only
# read access to its own secrets. (The default compute account has Editor on the whole project.)
if ! gcloud iam service-accounts describe "$SA_EMAIL" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$RUNTIME_SA" --display-name="Cloud Run runtime: $SERVICE"
fi

grant_secret() {
  gcloud secrets add-iam-policy-binding "$1" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role=roles/secretmanager.secretAccessor >/dev/null
}

# The demo password lives in Secret Manager, never in the repo or in plain env vars.
if ! gcloud secrets describe "$SECRET" >/dev/null 2>&1; then
  read -r -s -p "Demo password for the personas (min 8 chars): " DEMO_PASSWORD; echo
  printf '%s' "$DEMO_PASSWORD" | gcloud secrets create "$SECRET" --data-file=-
fi
grant_secret "$SECRET"
SECRETS="DEMO_PASSWORD=${SECRET}:latest"

# Kate's API keys, when they exist as secrets (create them the same way, e.g.
# `printf '%s' "$KEY" | gcloud secrets create gemini-api-key --data-file=-`).
for pair in GEMINI_API_KEY=gemini-api-key ELEVENLABS_API_KEY=elevenlabs-api-key; do
  name="${pair#*=}"
  if gcloud secrets describe "$name" >/dev/null 2>&1; then
    grant_secret "$name"
    SECRETS="${SECRETS},${pair%%=*}=${name}:latest"
  fi
done

# max-instances=1: demo data and sessions are in memory (see README "Known limitations").
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --service-account "$SA_EMAIL" \
  --allow-unauthenticated \
  --max-instances 1 \
  --memory 512Mi \
  --set-env-vars APP_ENV=production \
  --set-secrets "$SECRETS"
