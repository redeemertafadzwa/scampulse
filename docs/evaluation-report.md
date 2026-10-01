# ScamPulse — Evaluation Report

Measured on three held-out synthetic sets, each kept separate. The training CSV holds only 12 unique repeated messages, so accuracy on it is meaningless and is not reported here.

## TEST set (108 messages)
- Scam-vs-benign accuracy: **100.0%**

Per-threat-type (scam messages only):
```
                   precision    recall  f1-score   support

AI-Enabled Threat       0.00      0.00      0.00        12
   Financial Scam       0.80      0.80      0.80        30
   Identity Fraud       0.67      1.00      0.80        12
   Malicious Link       0.50      0.50      0.50        12
         Phishing       0.75      1.00      0.86        18

         accuracy                           0.71        84
        macro avg       0.54      0.66      0.59        84
     weighted avg       0.61      0.71      0.66        84

```
Confusion matrix (threat types):
```
[[ 0  6  0  6  0]
 [ 0 24  6  0  0]
 [ 0  0 12  0  0]
 [ 0  0  0  6  6]
 [ 0  0  0  0 18]]
labels: AI-Enabled Threat, Financial Scam, Identity Fraud, Malicious Link, Phishing
```

## Headline numbers
- **Scams wrongly cleared:** 0.8% (1/126 scam messages missed)  — lower is better
- **False alarms on legit:** 0.0% (0/96 genuine messages flagged)  — lower is better

## DISGUISED set (42 messages)
- Caught despite typos/leetspeak/mixed language: **97.6%** (41/42)

## LEGIT set (96 messages)
- Correctly left alone: **100.0%**

_See known-limitations.md for remaining failures._
