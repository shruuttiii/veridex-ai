"""Train and evaluate the Veridex text classifier on a real public dataset.

Dataset: UCI SMS Spam Collection (download yourself, do not invent data):
  https://archive.ics.uci.edu/dataset/228/sms+spam+collection
  Put either 'SMSSpamCollection' (tab-separated: label<TAB>text) or Kaggle's 'spam.csv' (v1,v2) in ./data/

Usage:  python train.py --data data/SMSSpamCollection
Outputs: model.joblib, metrics.json, confusion_matrix.png  (all numbers come from the held-out test set)
"""
import argparse, json, joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             confusion_matrix, classification_report, ConfusionMatrixDisplay)

def load(path):
    if path.lower().endswith(".csv"):
        df = pd.read_csv(path, encoding="latin-1").iloc[:, :2]
    else:
        df = pd.read_csv(path, sep="\t", header=None, encoding="latin-1", quoting=3)
    df.columns = ["label", "text"]
    df = df.dropna().drop_duplicates()
    df["y"] = (df["label"].str.strip().str.lower() == "spam").astype(int)
    return df

def main(path, seed=42):
    df = load(path)
    print(f"Rows after dropping duplicates: {len(df)} | scam/spam share: {df.y.mean():.1%}")
    Xtr, Xte, ytr, yte = train_test_split(df.text, df.y, test_size=0.2, stratify=df.y, random_state=seed)
    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2, lowercase=True),
        LogisticRegression(class_weight="balanced", max_iter=2000, C=4.0))
    model.fit(Xtr, ytr)
    p = model.predict_proba(Xte)[:, 1]
    out = {"dataset": path, "n_train": len(Xtr), "n_test": len(Xte), "thresholds": {}}
    # Report two operating points; lower threshold trades precision for fewer false negatives.
    for thr in (0.5, 0.3):
        pred = (p >= thr).astype(int)
        tn, fp, fn, tp = confusion_matrix(yte, pred).ravel()
        out["thresholds"][str(thr)] = dict(
            accuracy=accuracy_score(yte, pred), precision=precision_score(yte, pred),
            recall=recall_score(yte, pred), f1=f1_score(yte, pred),
            tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp))
        print(f"\n--- threshold {thr} ---")
        print(classification_report(yte, pred, target_names=["safe", "scam/spam"], digits=3))
        print(f"Confusion matrix  TN={tn} FP={fp} FN={fn} TP={tp}   (FN = scams we MISSED)")
    pred = (p >= 0.5).astype(int)
    ConfusionMatrixDisplay(confusion_matrix(yte, pred), display_labels=["Safe", "Scam"]).plot(cmap="Greens")
    import matplotlib.pyplot as plt; plt.title("Confusion matrix (test set, threshold 0.5)"); plt.savefig("confusion_matrix.png", dpi=150, bbox_inches="tight")
    json.dump(out, open("metrics.json", "w"), indent=2)
    joblib.dump(model, "model.joblib")
    print("\nSaved model.joblib, metrics.json, confusion_matrix.png")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--data", required=True)
    main(ap.parse_args().data)
