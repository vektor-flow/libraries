"""Single authorized completion notice through the existing app-server client.
No retries, new chats, dispatcher changes, or writes outside this directory.
"""
import datetime
import importlib.util
import json
from pathlib import Path
import sys
import uuid

sys.dont_write_bytecode = True
here = Path(__file__).resolve().parent
receipt = here / "notification-receipt.json"
if receipt.exists():
    raise SystemExit("Receipt already exists; refusing duplicate/ambiguous retry")
coordinator = "01a14893-cb1e-7203-97dd-de3da44dcf31"
message = (
    "DONE 01a14959-1ebe-7f00-8e66-b7b19808c048 | "
    "Corrected whole/nested-record projection candidate ready. "
    "Core53 SHA256 226bb513fec0c2e1d9443fd9ac61d6ab863e9a3a136ab2238cf7d9346130307f; "
    "complete ORIGINAL D288 baseline patch and small held-candidate delta. "
    "Counted Numeric/String children retained, fixed sibling 3->1/0 exact; canonical zero-width offsets and immutable snapshots addressed. "
    "Original tests and reviewer 27 cases/negatives unchanged; meaningful native additions supplied. "
    "29 source pins, 3 exact patch reconstructions, inherited 7 Python model tests pass; C++/VKF UNEXECUTED. "
    "Buildprep03 must rebind corrected SHA after review; its package untouched. All host children joined; no excluded overlap | "
    + str(here / "HANDOFF.txt")
)
state = {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
         "coordinator": coordinator, "message": message,
         "status": "preparing", "retries": 0}
receipt.write_text(json.dumps(state, indent=2) + "\n")
client = None
try:
    module_path = Path("/home/viktor/Projects/Vektor Flow/.worktrees/integration-0133/bootstrap/scripts/worker_supervisor_0136.py")
    spec = importlib.util.spec_from_file_location("existing_notification_client", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    client = module.Client("/home/viktor/snap/codex/34/app-server-control/app-server-control.sock")
    thread = client.rpc("thread/read", {"threadId": coordinator, "includeTurns": True})["thread"]
    turns = thread.get("turns", [])
    error = json.dumps((turns or [{}])[-1].get("error")).lower()
    if any(word in error for word in ("cyberpolicy", "safety", "flagged", "misalignment")):
        state["status"] = "held: coordinator service rejection; no retry"
    else:
        active = next((t for t in reversed(turns) if t.get("status") == "inProgress"), None)
        method = "turn/steer" if active else "turn/start"
        params = {"threadId": coordinator, "input": [{"type": "text", "text": message}]}
        if active:
            params["expectedTurnId"] = active["id"]
        else:
            params["clientUserMessageId"] = str(uuid.uuid5(uuid.NAMESPACE_URL, message))
        state.update(status="sending", method=method)
        receipt.write_text(json.dumps(state, indent=2) + "\n")
        state["ack"] = client.rpc(method, params)
        state["status"] = "acknowledged"
except Exception as exc:
    state.update(status="delivery_uncertain; no retry", error=str(exc))
finally:
    if client is not None:
        client.sock.close()
    receipt.write_text(json.dumps(state, indent=2) + "\n")
print(state["status"])
