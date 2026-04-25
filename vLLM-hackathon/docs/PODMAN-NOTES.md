# Podman vs. Docker

The official event prep page lists **Podman** in the required tools. Our Brev-based Launchables default to Docker because that's what the Brev base image ships. This doc clarifies which is required where and how to use Podman if you prefer.

## Quick reference

| Where | Works with Podman? | Works with Docker? | Notes |
|-------|:------------------:|:------------------:|-------|
| **Tier 1 / 2 / 3 Launchables** (vLLM, llm-d) | ✅ yes | ✅ yes | vLLM and llm-d don't require Docker specifically — any OCI runtime works. |
| **Track 4 Inference Gateway kit** | ✅ yes (via kind+Podman) | ✅ yes | `kind` has a Podman provider — set `KIND_EXPERIMENTAL_PROVIDER=podman` |
| **Track 6 Perf Lab** (Prometheus + Grafana stack) | ✅ yes (`podman-compose`) | ✅ yes (`docker compose`) | Compose file is provider-neutral; both commands work. |
| **ZeroClaw demo** (laptop) | ✅ yes | ✅ yes | Ollama is the only backend dep; neither runtime is strictly required. |
| **NemoClaw sandbox** (Tier 4) | ❌ **Docker required** | ✅ yes | NemoClaw's OpenShell runtime assumes Docker's socket API. |

**Bottom line:** if you're building for any track except **Track 5 (NemoClaw)**, Podman works fine. For Track 5 you need Docker specifically.

## Using Podman in scripts

Most of our scripts invoke `docker ...` directly. If you're on a Podman-only machine, either:

### Option 1: alias (simplest)

```bash
alias docker=podman
alias docker-compose='podman-compose'
```

Then run our scripts as-is. Works for 95% of cases.

### Option 2: source the detection shim

The shim at `scripts/container-runtime.sh` detects what's available and exposes `$CONTAINER_RUNTIME` and `$COMPOSE_CMD`:

```bash
source scripts/container-runtime.sh

$CONTAINER_RUNTIME ps              # → docker ps OR podman ps
$COMPOSE_CMD up -d                 # → docker compose up -d OR podman-compose up -d
```

### Option 3: Brev instance

Brev instances come with Docker pre-installed and working. If you're hacking on Brev, just use the default — no reason to switch.

## Known Podman gotchas

### Rootless + GPU

Rootless Podman doesn't pass GPUs through by default. Use `podman run --device nvidia.com/gpu=all` (CDI spec) or fall back to rootful Podman (`sudo podman ...`) for containers that need GPU access.

### Networking in `kind`

`kind create cluster` supports Podman via `KIND_EXPERIMENTAL_PROVIDER=podman`, but network plugins differ. If `kubectl get nodes` returns NotReady for too long, check `podman network ls` and ensure the `kind` network exists.

### Compose file compatibility

`podman-compose` lags behind `docker compose` on newer compose features (e.g., GPU resource requests in the `deploy` section). Our `track6-perf-lab/docker-compose.yaml` uses `network_mode: host` specifically to avoid these edge cases — both runtimes handle it identically.

### NemoClaw

NemoClaw's `nemoclaw onboard` command invokes `docker` directly and checks for the Docker socket at `/var/run/docker.sock`. There's no supported way to point it at Podman — if you need NemoClaw, install Docker. Running Docker and Podman side-by-side on the same machine is fine.

## References

- [kind with Podman provider](https://kind.sigs.k8s.io/docs/user/rootless/)
- [Podman CDI for NVIDIA GPUs](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html#step-2-generate-a-cdi-specification)
- [podman-compose](https://github.com/containers/podman-compose)
