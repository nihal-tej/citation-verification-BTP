Below is the final metadata reference table for our Indian Legal RAG project. You can use it while implementing PDF extraction and designing the JSON schema.

## 1. Identification metadata

| Metadata field       | What it captures                             | Example                          |
| -------------------- | -------------------------------------------- | -------------------------------- |
| `case_id`            | Unique internal ID assigned to each judgment | `SC_2025_0001`                   |
| `case_title`         | Official name of the case                    | Mamman Khan v. State of Haryana  |
| `case_number`        | Official case number                         | Criminal Appeal No. 4002 of 2025 |
| `neutral_citation`   | Official neutral citation, if available      | `2025 INSC 1113`                 |
| `reporter_citations` | Citations in law reports                     | `[2025] 10 S.C.R. 131`           |
| `decision_date`      | Date the court delivered the judgment        | `2025-09-12`                     |
| `document_type`      | Type of legal document                       | Judgment, order, review petition |
| `language`           | Language of the document                     | English                          |

## 2. Court details

| Metadata field    | What it captures                                     | Example                                   |
| ----------------- | ---------------------------------------------------- | ----------------------------------------- |
| `court_name`      | Court delivering the judgment                        | Supreme Court of India                    |
| `court_level`     | Level of court                                       | Supreme Court, High Court, District Court |
| `jurisdiction`    | Legal or territorial jurisdiction, when identifiable | Criminal appellate jurisdiction           |
| `bench`           | Bench composition or bench size                      | Two-judge bench                           |
| `judges`          | All judges who heard the case                        | J.B. Pardiwala, R. Mahadevan              |
| `author_judge`    | Judge who authored the judgment                      | R. Mahadevan                              |
| `court_of_origin` | Higher court from which the matter came              | Punjab and Haryana High Court             |
| `lower_court`     | Original or subordinate court involved               | Additional Sessions Judge, Nuh            |

## 3. Parties

| Metadata field  | What it captures                                               | Example                                       |
| --------------- | -------------------------------------------------------------- | --------------------------------------------- |
| `appellants`    | Parties appealing against the challenged decision              | Appellant's name or names                     |
| `respondents`   | Parties responding to the appeal                               | State of Haryana                              |
| `other_parties` | Other relevant parties, such as intervenors or accused persons | Co-accused or intervenor details, if relevant |

## 4. Proceedings and procedural history

| Metadata field              | What it captures                                                 | Example                                              |
| --------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------- |
| `case_type`                 | Broad nature of the proceeding                                   | Criminal appeal                                      |
| `originating_case_numbers`  | Case numbers from earlier proceedings                            | Original trial or High Court case numbers            |
| `connected_cases`           | Other related cases decided or considered alongside the judgment | Criminal Appeal No. 4003 of 2025                     |
| `lower_court_case_numbers`  | Case numbers assigned by subordinate courts                      | Sessions trial number                                |
| `lower_court_order_dates`   | Dates of the specific orders challenged                          | `2024-08-28`, `2024-09-02`                           |
| `lower_court_decision_date` | Date of the relevant earlier judgment or decision                | `2024-12-12`                                         |
| `procedural_history`        | Sequence of important procedural events                          | FIR → trial proceedings → High Court → Supreme Court |

## 5. Legal context

| Metadata field      | What it captures                                                  | Example                                                 |
| ------------------- | ----------------------------------------------------------------- | ------------------------------------------------------- |
| `acts_and_statutes` | Names of laws relevant to the judgment                            | Code of Criminal Procedure, 1973                        |
| `legal_provisions`  | Specific sections, articles, rules, or regulations considered     | CrPC Sections 218–223; Constitution Articles 14 and 21  |
| `subject_tags`      | Standardized categories for filtering and retrieval               | Criminal procedure, joint trial, equality               |
| `legal_issues`      | Main legal disputes addressed by the court                        | Whether separate trials were justified                  |
| `questions_of_law`  | Precise legal questions the court had to answer                   | Whether the separation of trial was legally sustainable |
| `headnote`          | Publisher-provided or judgment-provided headnote, where available | Existing headnote text                                  |
| `keywords`          | Short terms describing the judgment                               | Separate trial, co-accused, fair trial                  |

Difference: `legal_issues` describes the dispute broadly; `questions_of_law` states the specific question requiring a legal answer.

## 6. Case analysis — most important for similar-case retrieval

| Metadata field           | What it captures                                                      | How it helps retrieval                                      |
| ------------------------ | --------------------------------------------------------------------- | ----------------------------------------------------------- |
| `case_summary`           | Concise overview of facts, dispute, reasoning, and outcome            | Provides an overall semantic representation of the judgment |
| `material_facts`         | Facts that materially influenced the court's decision                 | Finds cases with similar factual circumstances              |
| `arguments_appellant`    | Main arguments advanced by the appellant                              | Finds cases involving similar submissions                   |
| `arguments_respondent`   | Main arguments advanced by the respondent                             | Helps compare opposing legal positions                      |
| `court_findings`         | Findings or conclusions reached by the court on particular issues     | Identifies how the court resolved disputed matters          |
| `legal_principles`       | Legal rules or principles articulated or applied by the court         | Finds judgments discussing similar legal doctrines          |
| `decision_reasoning`     | The court's explanation for reaching its conclusion                   | Finds cases with similar legal reasoning                    |
| `distinguishing_factors` | Important circumstances that distinguish this case from similar cases | Helps explain why apparently similar cases may differ       |

## 7. Outcome

| Metadata field      | What it captures                                                       | Example                                                          |
| ------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `disposition`       | Overall result of the proceeding                                       | Appeal allowed, dismissed, partly allowed                        |
| `final_order`       | Operative order made by the court                                      | Challenged orders set aside                                      |
| `relief_granted`    | Relief actually granted to the parties                                 | Relief against separation of trial                               |
| `directions_issued` | Specific directions given by the court                                 | Directions to conduct further proceedings                        |
| `remand_details`    | Whether the matter was sent back, to which court, and for what purpose | Matter remitted to the appropriate court for further proceedings |

## 8. Provenance and validation

| Metadata field      | What it captures                                               | Example                                   |
| ------------------- | -------------------------------------------------------------- | ----------------------------------------- |
| `source_pdf`        | Original PDF filename or source reference                      | `judgment.pdf`                            |
| `page_count`        | Number of pages in the source PDF                              | `21`                                      |
| `extraction_method` | How the information was extracted                              | PyMuPDF + Qwen                            |
| `field_evidence`    | Supporting page numbers and text excerpts for extracted fields | Decision date supported by text on page 1 |
| `review_status`     | Whether the extracted metadata has been checked                | `pending`, `verified`, `needs_review`     |

## 9. Which fields should we use for similarity search?

Not every metadata field should be embedded into a vector. We should separate semantic retrieval fields from filtering fields.

| Purpose                      | Fields to use                                              |
| ---------------------------- | ---------------------------------------------------------- |
| Main similarity search       | `case_summary`, `material_facts`, `legal_issues`           |
| Legal reasoning similarity   | `legal_principles`, `decision_reasoning`, `court_findings` |
| Search by statute            | `acts_and_statutes`, `legal_provisions`                    |
| Filter by court or time      | `court_name`, `court_level`, `decision_date`               |
| Filter by proceeding type    | `case_type`, `document_type`                               |
| Compare results and outcomes | `disposition`, `final_order`, `distinguishing_factors`     |
| Verify extracted information | `field_evidence`, `review_status`                          |

### My recommendation

For the first version, keep all eight sections in the schema, but prioritize reliable extraction of identification, court details, parties, proceedings, legal context, and outcome. Use Qwen to generate the case-analysis fields, then validate those fields against the judgment.

One important distinction: the case summary and analysis fields are derived metadata, while information such as the case title, decision date, and printed headnote should be extracted from the document whenever possible. This separation will help us identify extraction errors and improve the quality of future similar-case retrieval.