# Interview guide, walkthrough and AI disclosure: Nyaya Sahayak (Problem 2)

## 3-minute walkthrough

| Time | Show | Say |
|---|---|---|
| 0:00 to 0:20 | README intro | "Most people never get help for a withheld deposit, a missing refund or unpaid salary. I built a narrow assistant for exactly those three, which says honestly when something is outside what it knows." |
| 0:20 to 1:10 | `python3 app.py web`; paste case c02 turn 1, then turn 2 | "First message is vague, so it asks for the amount, date, state and the other side's name. Second message: it builds the case. ₹60,000, Karnataka worked out from 'Bengaluru', the proof I have and the proof I'm missing, my options in order, and a draft legal notice with blanks instead of invented facts." |
| 1:10 to 1:40 | Expand "Sources" | "Every legal sentence carries an ID and a source link, marked official, secondary or general. It can only say what's in this 14-entry file." |
| 1:40 to 2:20 | Case c15 or test G02/M01 in the terminal | "**Design decision:** a closed knowledge base plus a guard. If a model says 'Section 420 IPC' or invents an Act, a case name or an amount, its text is thrown away and the sourced answer stands. Without a model, nothing is generated at all." |
| 2:20 to 2:45 | Case c13, the time-barred one | "It warns that 34 months is past the 2-year consumer limit and sends the person to a lawyer quickly." |
| 2:45 to 3:00 | The "not covered" list | "**Limitation:** three problem types, state rent laws not encoded, and the legal content hasn't been reviewed by a lawyer. That review would be my first step before any real user." |

## Likely questions

**Why only three problem types?**
The brief allows depth over breadth. These three are high-frequency, money-based and mostly civil, with clear first steps. Being wrong about criminal or family matters is far more costly. Those are detected and routed to legal aid.

**How do you stop hallucinated law?**
- The reply is assembled from a closed, sourced knowledge base. That is a structural guarantee, not a prompt request.
- The model is optional and can only rephrase.
- The guard rejects any unknown citation, section, Act, case name, amount or promised outcome.
- Tests G02 to G05 and M01 prove this.

**Why not RAG over all of India Code?**
Retrieval narrows the source but the model can still mis-summarise it, and checking a summary against a whole statute is hard. With 14 hand-checked statements I can test every one. Retrieval is the next step once a lawyer has reviewed the base.

**Your sources are partly secondary. Isn't that risky?**
Yes, and the tool says so: each statement shows its verification level. Before production, a lawyer re-checks each entry against the official text and the knowledge base gets an owner and a review date. Laws change: the labour codes changed on 21 Nov 2025.

**What does the AI actually do, then?**
In the baseline, nothing generative. The "intelligence" is structured intake: amounts, dates, state, evidence and contradictions in three languages. The model adds natural explanations in the user's language. That is the part where a stronger model (for example one Kuku provides) helps, and it's swappable with a flag.

**What happens with contradictory facts?**
It keeps both values, asks which is right, and leaves the amount in the notice as a blank (case c07).

**Urgent or dangerous situations?**
Safety numbers come first (112, 181, 1930). Deadlines, evictions, summons and time limits trigger a "see a lawyer or legal aid today" message.

**How would you know it works?**
- Share of conversations that end with a complete case summary and a sent notice or helpline filing.
- Lawyer-rated accuracy on a sample, with a target of zero incorrect legal statements.
- Escalation recall on urgent cases (100% on the scripted ones).
- User follow-up at 30 days: was the money recovered or the grievance registered?

**Scale and cost.**
The deterministic core is free and instant. The model is one short call per turn (about 1 to 2k tokens), so cheap at small-model prices. The real cost is keeping the legal content accurate: a lawyer-owned review cycle.

## AI usage disclosure

- **Built with Claude Code (Claude Opus 5.5):** the legal research searches, the code, the tests and draft docs. Claude checked each knowledge-base entry against the sources it cites; the candidate has not yet re-checked them, and no lawyer has reviewed them. [Candidate: re-check before submitting.]
- **Where the AI got it wrong:** it wrote a guard that flagged its own citation tags. `[CPC-20]` contains "CPC", so the guard would reject correct model text. Test G01 caught it, and the fix removes citation tags before checking.
- **A second case:** its first evidence-negation rule only negated the last noun in "no agreement or receipt", so the tool claimed the user had an agreement they had just said they didn't have. Case c06 caught it.
