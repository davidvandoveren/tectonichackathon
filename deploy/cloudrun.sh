#!/usr/bin/env bash
# Deploy to Google Cloud Run straight from source (Cloud Build builds the Dockerfile).
# Usage: PROJECT_ID=my-project ./deploy/cloudrun.sh
#
# Kate's real AI (Gemini) and voice (ElevenLabs) are optional. Their keys live in Secret Manager,
# like the demo password. The first deploy asks for them (Enter = skip, Kate stays in demo mode);
# pass GEMINI_API_KEY / ELEVENLABS_API_KEY in the environment to set or rotate them without a
# prompt. Non-secret settings (voice ids, ADMIN_USERNAMES, PASSWORDLESS_LOGIN, KATE_LLM_PROVIDER)
# are passed through when set in the environment.
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-europe-west1}"
SERVICE="${SERVICE:-tectonichackathon}"
SECRET="${SECRET:-demo-password}"
GEMINI_SECRET="${GEMINI_SECRET:-gemini-api-key}"
ELEVENLABS_SECRET="${ELEVENLABS_SECRET:-elevenlabs-api-key}"

gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
RUNTIME_SA="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

grant_access() {
  gcloud secrets add-iam-policy-binding "$1" --member="$RUNTIME_SA" \
    --role=roles/secretmanager.secretAccessor >/dev/null
}

# The demo password lives in Secret Manager, never in the repo or in plain env vars.
if ! gcloud secrets describe "$SECRET" >/dev/null 2>&1; then
  read -r -s -p "Demo password for the personas (min 8 chars): " DEMO_PASSWORD; echo
  printf '%s' "$DEMO_PASSWORD" | gcloud secrets create "$SECRET" --data-file=-
fi
grant_access "$SECRET"
SECRETS="DEMO_PASSWORD=${SECRET}:latest"

# optional_secret ENV_NAME SECRET_NAME LABEL
# Uses the value from the environment (creates the secret or adds a new version), otherwise asks
# once when the secret does not exist yet. An empty answer skips it: the app then runs without it.
optional_secret() {
  local env_name="$1" secret_name="$2" label="$3" value="${!1:-}"
  if gcloud secrets describe "$secret_name" >/dev/null 2>&1; then
    if [[ -n "$value" ]]; then
      printf '%s' "$value" | gcloud secrets versions add "$secret_name" --data-file=- >/dev/null
    fi
  else
    if [[ -z "$value" && -t 0 ]]; then
      read -r -s -p "$label (Enter = skip): " value; echo
    fi
    if [[ -z "$value" ]]; then
      echo "Skipping $env_name: Kate runs without it."
      return
    fi
    printf '%s' "$value" | gcloud secrets create "$secret_name" --data-file=- >/dev/null
  fi
  grant_access "$secret_name"
  SECRETS="${SECRETS},${env_name}=${secret_name}:latest"
}

optional_secret GEMINI_API_KEY "$GEMINI_SECRET" "Gemini API key for Kate's chat"
optional_secret ELEVENLABS_API_KEY "$ELEVENLABS_SECRET" "ElevenLabs API key for Kate's voice"

# Plain (non-secret) settings: only passed when set, so the app defaults apply otherwise.
# "^@^" makes '@' the list separator, so values may contain commas (ADMIN_USERNAMES=a,b).
ENV_VARS="APP_ENV=production"
for name in KATE_LLM_PROVIDER GEMINI_MODEL ELEVENLABS_VOICE_ID_FEMALE ELEVENLABS_VOICE_ID_MALE \
  ELEVENLABS_VOICE_ID ADMIN_USERNAMES PASSWORDLESS_LOGIN; do
  if [[ -n "${!name:-}" ]]; then
    ENV_VARS="${ENV_VARS}@${name}=${!name}"
  fi
done

# max-instances=1: demo data and sessions are in memory (see README "Known limitations").
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --max-instances 1 \
  --memory 512Mi \
  --set-env-vars "^@^${ENV_VARS}" \
  --set-secrets "$SECRETS"
