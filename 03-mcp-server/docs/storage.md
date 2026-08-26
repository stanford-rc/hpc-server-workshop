# Storage and quotas

Sherlock gives every user several storage spaces with different quotas,
performance, and retention rules.

| Space | Quota | Retention | Best for |
|-------|-------|-----------|----------|
| `$HOME` | 15 GB | Permanent | Code, configs, small scripts |
| `$GROUP_HOME` | 1 TB | Permanent | Shared group code and software |
| `$SCRATCH` | 100 TB | Purged after 90 days | Active job I/O, checkpoints |
| `$GROUP_SCRATCH` | 100 TB | Purged after 90 days | Shared active datasets |
| `$OAK` | Purchased | Long-term | Published datasets, archives |

## Checking your usage

Run `sh_quota` to see current usage against every quota at once. A job that
fails with "Disk quota exceeded" is almost always `$HOME` filling up — check
`~/.cache` first, which is safe to empty.

## Choosing a space

Write job output to `$SCRATCH` for speed, then move anything you need to keep
to `$OAK` before the 90-day purge. Never write large job output to `$HOME`;
the 15 GB quota fills quickly and a full `$HOME` breaks interactive sessions.
