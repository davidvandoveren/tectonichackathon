import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { getAccounts } from "../api/accounts";
import { createTransfer } from "../api/transfers";
import { ApiError } from "../api/client";
import type { Account, Transaction } from "../api/types";
import { formatIban, isValidIban, normalizeIban } from "../lib/iban";
import { formatMoney, isValidAmount, toAmountString } from "../lib/money";
import { PageHeader } from "../components/PageHeader";
import { Button } from "../components/Button";
import { TextField } from "../components/TextField";
import { SelectField } from "../components/SelectField";
import { Skeleton } from "../components/Skeleton";
import { ErrorState } from "../components/ErrorState";
import styles from "./TransferPage.module.css";

type Step = "form" | "review" | "success";

interface FormErrors {
  fromAccountId?: string;
  toName?: string;
  toIban?: string;
  amount?: string;
  description?: string;
}

const MAX_AMOUNT = 10000;
const MAX_NAME_LENGTH = 70;
const MAX_DESCRIPTION_LENGTH = 140;

export function TransferPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [fromAccountId, setFromAccountId] = useState<string>(searchParams.get("from") ?? "");
  const [toName, setToName] = useState("");
  const [toIban, setToIban] = useState("");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");

  const [errors, setErrors] = useState<FormErrors>({});
  const [step, setStep] = useState<Step>("form");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdTransaction, setCreatedTransaction] = useState<Transaction | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getAccounts(controller.signal)
      .then((data) => {
        setAccounts(data);
        setFromAccountId((current) => current || data[0]?.id || "");
      })
      .catch((error: unknown) => {
        setLoadError(error instanceof ApiError ? error.detail : "Kan rekeningen niet laden.");
      });
    return () => controller.abort();
  }, []);

  const fromAccount = useMemo(
    () => accounts?.find((account) => account.id === fromAccountId) ?? null,
    [accounts, fromAccountId]
  );

  function validate(): boolean {
    const nextErrors: FormErrors = {};

    if (!fromAccountId) {
      nextErrors.fromAccountId = "Kies een rekening.";
    }
    if (toName.trim().length < 1 || toName.trim().length > MAX_NAME_LENGTH) {
      nextErrors.toName = `Naam moet tussen 1 en ${MAX_NAME_LENGTH} tekens zijn.`;
    }
    if (!isValidIban(toIban)) {
      nextErrors.toIban = "Ongeldig IBAN-nummer.";
    }
    if (!isValidAmount(amount, MAX_AMOUNT)) {
      nextErrors.amount = `Voer een bedrag groter dan 0 in, max. €${MAX_AMOUNT.toLocaleString("nl-BE")} en max. 2 decimalen.`;
    }
    if (description.length > MAX_DESCRIPTION_LENGTH) {
      nextErrors.description = `Maximaal ${MAX_DESCRIPTION_LENGTH} tekens.`;
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  function handleReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (validate()) {
      setStep("review");
    }
  }

  async function handleConfirm() {
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const transaction = await createTransfer({
        from_account_id: fromAccountId,
        to_iban: normalizeIban(toIban),
        to_name: toName.trim(),
        amount: toAmountString(amount),
        description: description.trim(),
      });
      setCreatedTransaction(transaction);
      setStep("success");
    } catch (error) {
      if (error instanceof ApiError) {
        setSubmitError(
          error.status === 429 ? "Te veel pogingen. Probeer het straks opnieuw." : error.detail
        );
      } else {
        setSubmitError("Overschrijving is mislukt. Probeer het opnieuw.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  if (loadError) {
    return (
      <div className={styles.page}>
        <PageHeader title="Overschrijven" showBack />
        <div className={styles.content}>
          <ErrorState message={loadError} />
        </div>
      </div>
    );
  }

  if (!accounts) {
    return (
      <div className={styles.page}>
        <PageHeader title="Overschrijven" showBack />
        <div className={styles.content}>
          <Skeleton height={220} />
        </div>
      </div>
    );
  }

  if (step === "success" && createdTransaction) {
    return (
      <div className={styles.page}>
        <PageHeader title="Gelukt" />
        <div className={styles.content}>
          <div className={styles.successCard} role="status">
            <p className={styles.successTitle}>Overschrijving verstuurd</p>
            <p className={styles.successAmount}>
              {formatMoney(createdTransaction.amount, createdTransaction.currency)}
            </p>
            <p>Naar: {createdTransaction.counterparty}</p>
            <p>{formatIban(toIban)}</p>
            {createdTransaction.description && <p>Mededeling: {createdTransaction.description}</p>}
            <Button type="button" onClick={() => navigate("/")}>
              Terug naar Home
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (step === "review") {
    return (
      <div className={styles.page}>
        <PageHeader title="Controleer overschrijving" />
        <div className={styles.content}>
          <dl className={styles.reviewList}>
            <div className={styles.reviewRow}>
              <dt>Van</dt>
              <dd>{fromAccount?.name}</dd>
            </div>
            <div className={styles.reviewRow}>
              <dt>Naar</dt>
              <dd>{toName}</dd>
            </div>
            <div className={styles.reviewRow}>
              <dt>IBAN</dt>
              <dd>{formatIban(toIban)}</dd>
            </div>
            <div className={styles.reviewRow}>
              <dt>Bedrag</dt>
              <dd>{formatMoney(toAmountString(amount), fromAccount?.currency ?? "EUR")}</dd>
            </div>
            {description && (
              <div className={styles.reviewRow}>
                <dt>Mededeling</dt>
                <dd>{description}</dd>
              </div>
            )}
          </dl>

          {submitError && (
            <p className={styles.submitError} role="alert" aria-live="assertive">
              {submitError}
            </p>
          )}

          <div className={styles.reviewActions}>
            <Button type="button" variant="secondary" onClick={() => setStep("form")} disabled={isSubmitting}>
              Aanpassen
            </Button>
            <Button type="button" onClick={handleConfirm} disabled={isSubmitting}>
              {isSubmitting ? "Bezig…" : "Bevestigen"}
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <PageHeader title="Overschrijven" showBack />
      <div className={styles.content}>
        <form className={styles.form} onSubmit={handleReview} noValidate>
          <SelectField
            label="Van rekening"
            value={fromAccountId}
            error={errors.fromAccountId}
            onChange={(event) => setFromAccountId(event.target.value)}
          >
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name} · {formatMoney(account.balance, account.currency)}
              </option>
            ))}
          </SelectField>

          <TextField
            label="Naam begunstigde"
            value={toName}
            maxLength={MAX_NAME_LENGTH}
            error={errors.toName}
            onChange={(event) => setToName(event.target.value)}
          />

          <TextField
            label="IBAN"
            value={toIban}
            error={errors.toIban}
            onChange={(event) => setToIban(event.target.value)}
            placeholder="BE68 5390 0754 7034"
          />

          <TextField
            label="Bedrag (EUR)"
            inputMode="decimal"
            value={amount}
            error={errors.amount}
            onChange={(event) => setAmount(event.target.value)}
            placeholder="0,00"
          />

          <TextField
            label="Mededeling (optioneel)"
            value={description}
            maxLength={MAX_DESCRIPTION_LENGTH}
            error={errors.description}
            onChange={(event) => setDescription(event.target.value)}
          />

          <Button type="submit" fullWidth>
            Volgende
          </Button>
        </form>
      </div>
    </div>
  );
}
