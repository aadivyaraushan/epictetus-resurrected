# Review chapter evidence plan

```text
RAG source events during call
          |
          v
unique Book / Chapter + title list
          |
          +--> read-only completed review section
          |
          +--> saved Notion review section
```

## Done means

- The completed review no longer shows the `/ 01` suffix.
- Every non-empty RAG source event contributes a unique chapter entry, while
  empty events only clear the live panel and do not erase call history.
- The completed review shows the accumulated list read-only.
- Saving the review includes a `Chapters referenced` section in the Notion page.
- Existing transcript, summary, next-step, source-panel, and save behavior stay
  unchanged.

## Build and prove

1. Add failing tests for chapter accumulation, review rendering, Notion payload,
   and removal of the `/ 01` label.
2. Thread the accumulated chapter list from the live source panel through the
   call review model.
3. Render it read-only and include it in the saved Notion artifact.
4. Run the web tests and production build, then drive the public page far enough
   to verify the review screen.
5. Have an independent judge check the finished behavior and evidence.
