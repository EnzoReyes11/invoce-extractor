2026-03-13
Created an invoice extractor. It will extract a JSON from a pdf invoice, reciept, etc.
It's very basic. It uses a pre defined JSON Schema as a template.

I know already that for Claro invoices, it's not functioning very well. The line items are not extracted correctly, it confuses
product description with actual product items.

## Next steps:
- Think how to make it work with Claro.  Maybe have a validating Agent the determines problematic documents and uses a different approach to extract data.
Like a custom extractor for Claro.
- Make it more robust and fault tolerant.
- Connect it with my google drive or cloud Storage.
- I will need to create another tool that can read my emails and extract from the email, or download a file from the email and pass it to the extractor.
- Get the output from the extractor and upload it to Bigquey (maybe through cloud Storage)
- How will this be run? Now it's an Agent that it's called by an user, but it should be part of a workflow.