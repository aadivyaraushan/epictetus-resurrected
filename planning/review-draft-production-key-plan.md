# Review draft production fix

```text
Existing key in local .env
        |
        v
Vercel Production OPENAI_API_KEY
        |
        v
Redeploy web app
        |
        v
Live draft request -> summary JSON -> review screen
```

## Done when

- Vercel Production has `OPENAI_API_KEY` without exposing its value.
- The production deployment is Ready.
- A real `/api/review/draft` request returns a summary and next step.
- The browser review screen no longer shows the automatic-draft failure.
- Vercel logs show a successful draft response and no missing-key error.

## Checks

1. Add the existing local key to Vercel Production through the Vercel CLI.
2. Deploy the `high` Luna reasoning request.
3. Send short and full browser smoke requests and inspect their responses/logs.
4. Run the existing tests/build.

## Result

- Production deployment `dpl_5RLHczRmA11DR1WwAuntstGP1ewU` is Ready.
- A direct production draft request returned HTTP 200 with a summary and next step.
- A full browser call returned a summary with no automatic-draft failure and no browser errors.
- Vercel logs recorded `produced summary_chars=124 next_step=false` for the browser call.
- Web tests passed 56/56 and the production build passed.
