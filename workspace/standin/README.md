# Stand-in image

**This is not Xill4 and does not behave like it.** It is a ~40-line container that does the
three things the sandbox harness depends on, and nothing else:

- serves HTTP on port 8000
- connects to `XILL4_DATABASE_CONNECTION_STRING` and writes a document
- runs as a non-root uid and writes a file into `/data/target`

Its only purpose is to let `workspace/preflight.py` and the provisioning path be exercised
end to end on a machine that cannot reach the private registry. A green preflight against
the stand-in proves the *harness* works; it proves nothing whatsoever about Xill4.

```
docker build -t xill4-standin:dev workspace/standin
python workspace/preflight.py --image xill4-standin:dev
```
