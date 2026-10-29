# AI provider terms and client consent (DRAFT, needs a lawyer's review)

Status: draft written 2026-10-29 from the providers' published terms. It is not legal advice. Have
a lawyer in your country review it before you use it with paying clients.

Each client job and Audit sends the client's code to one AI provider. Before starting, the founder
confirms in Mission Control that the client agreed. The confirm dialog shows the facts below,
from `app/platform/clients/provider_terms.py`, and the job records which version of those facts
was shown (`consent_terms` on `platform_client_work` and `platform_client_audits`).

## What the providers' terms say (read 2026-10-29)

| | DeepSeek (API) | OpenAI (API) |
|---|---|---|
| Company | Hangzhou DeepSeek Artificial Intelligence Co., Ltd. | OpenAI |
| Where data is stored and processed | People's Republic of China | United States by default. Other regions need sales approval (data residency). |
| Used to train their models | The privacy policy allows it, with an opt-out by email to privacy@deepseek.com. The API terms say nothing either way. | No, unless the account opts in to data sharing (off by default) |
| How long it's kept | No fixed period ("as long as you have an account") | Up to 30 days of abuse-monitoring logs. We set `store: false`, so responses aren't kept, and we don't use Files or Batches. |
| Zero retention | Not offered | Only with OpenAI's approval |
| Who owns inputs and outputs | The customer (API terms §4.2) | The customer |
| Governing law | Mainland China (API terms §10.1) | Per OpenAI's services agreement (not checked here) |
| Duty placed on us | Get end users' consent or another legal basis for any personal data, and disclose our privacy policy (API terms §3.3, §5.5) | Follow the usage policies and the DPA if we sign one |

Sources:
- DeepSeek Open Platform Terms of Service (effective 2026-04-29): https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html
- DeepSeek Privacy Policy (updated 2026-02-10): https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html
- OpenAI "Your data" (API): https://developers.openai.com/api/docs/guides/your-data
- OpenAI Enterprise privacy: https://openai.com/enterprise-privacy/

Uncertain points:
- **DeepSeek training on API data.** The API terms don't mention it. The privacy policy covers inputs in general and allows training, so this table assumes it may happen. Get DeepSeek's answer in writing if it matters to a client.
- **OpenAI account settings.** Whether our OpenAI organisation has opted in to data sharing is a dashboard setting. Check it (Settings → Data controls) before relying on the "not used for training" row.
- **OpenAI response storage.** Our OpenAI calls set `store: false`. So OpenAI keeps only its abuse-monitoring logs, up to 30 days, and not the 30-day response storage the Responses API uses by default.
- **What I couldn't read directly.** The OpenAI enterprise-privacy page blocked automated reading. The OpenAI row comes from its developer docs.

## Practical guidance

- **Code containing personal data, secrets or regulated data.** Examples: customer databases in fixtures, `.env` files, health or payment data. Use OpenAI rather than DeepSeek, or remove that data first. Many organisations' policies, and some governments', don't allow sending data to China-hosted AI services.
- **Choose the provider before the client agrees.** The dialog names the provider configured in Settings at that moment, and the job stays on it. If you switch providers, the next job needs fresh consent.
- **The founder's confirmation is only a record.** It notes that the client agreed; it isn't the agreement itself. Keep the client's written agreement, such as an email or a signed engagement letter, with your client records.

## Draft clause for the client agreement

> **Use of AI services.** To perform the work, [Your business] uses AI services provided by
> third parties. For each piece of work, [Your business] will tell you which AI service will be
> used before the work starts. Currently this is [DeepSeek, operated by Hangzhou DeepSeek
> Artificial Intelligence Co., Ltd. / OpenAI]. To do the work, copies of the relevant parts of
> your source code and related files will be sent to that service.
>
> You agree that:
> (a) your code may be stored and processed by that service in [the People's Republic of China / the
> United States], under that service's own terms and privacy policy, which [Your business] will give
> you on request;
> (b) [DeepSeek only:] that service's terms allow it to keep the data for as long as our account
> exists and to use it to improve its models; [OpenAI only:] that service keeps the data for up to
> 30 days for abuse monitoring and does not use it to train its models under our account settings;
> (c) you will tell [Your business] before the work starts if your code contains personal data,
> passwords, keys or other secrets, or data subject to legal restrictions. [Your business] will then
> agree with you whether to remove it, use a different AI service or not use AI for that work; and
> (d) you have the right to share the code with [Your business] for this purpose.
>
> [Your business] runs the AI's commands in an isolated environment, works on a copy of your code
> and does not change your original code. You review and accept every change before it is applied.
> [Your business] does not sell your code or use it for any purpose other than your work.
>
> You may withdraw this agreement at any time for future work by telling [Your business] in
> writing. This does not affect data already sent to an AI service, which stays subject to that
> service's terms.

Short version to send by email before a job:

> Before we start "[job title]" on [codebase]: we'll send a copy of the code to [provider] ([where
> it's stored]). [Provider facts from the Mission Control dialog.] Your original code isn't changed,
> and you review every change. Please reply "agreed" if that's OK, and tell us if the code contains
> personal data or secrets.

## For the lawyer to check

1. Whether this clause is enough consent, or another legal basis, under the data-protection law that applies to you and your clients (for example PDPA, GDPR or UK GDPR), especially for transfers to China.
2. Whether you need a data processing agreement with each client, and with OpenAI (OpenAI offers a DPA; DeepSeek doesn't publish one).
3. Liability and warranty wording for AI-written code, which isn't covered here.
4. Whether clients in regulated sectors (finance, health, government) need stricter terms or a no-DeepSeek rule.
5. Confidentiality and IP clauses in your existing client contract that might conflict with this one.

## Keeping it current

Re-read the four sources at least every three months, and whenever a provider announces a terms
change. If anything changed, update `TERMS` in `provider_terms.py`, set `checked` to the date you
re-read them, and update the table above. Changing `checked` changes the version. Any open
Mission Control page then has to reload, so nobody consents to the old facts.
