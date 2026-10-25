"""Second, independent critic: ask GPT (Codex on the VM, through the effiency relay inbox) to grade critic packets.

Copies each packet into <relay-repo>/.relay/tasks/critic-<id>/ with a delegate request; the VM worker runs Codex,
which reads prompt.md, views the images and writes critique_gpt.json there.  Commit and push the relay repo
afterwards (docs/vm-inbox.md in cogito5170/effiency); bring the answers back with --collect.

    python3 scripts/gpt_critic.py --relay-repo ../effiency PACKET_DIR...      (PACKET_DIR = .../<id>/critic)
    python3 scripts/gpt_critic.py --relay-repo ../effiency --collect PACKET_DIR...
"""
import argparse
import json
import os
import shutil
import sys
import time

ap = argparse.ArgumentParser()
ap.add_argument("--relay-repo", required=True)
ap.add_argument("--collect", action="store_true")
ap.add_argument("packets", nargs="+")
args = ap.parse_args()

INSTRUCTION = ("You are an editorial design juror. In {t}/ read prompt.md and aesthetic_criteria.md, then open and "
               "look at candidate.jpg, every zoom_*.jpg and every canon_*.jpg with your image viewing tool. Judge the "
               "candidate beside the canon pages exactly as prompt.md says and write ONLY {t}/critique_gpt.json in "
               "the JSON form it gives (Korean grade words, as listed). Do not change any other file.")

for p in args.packets:
    pid = os.path.basename(os.path.dirname(os.path.abspath(p)))
    t = f".relay/tasks/critic-{pid}"
    dst = os.path.join(args.relay_repo, t)
    if args.collect:
        f = os.path.join(dst, "critique_gpt.json")
        if os.path.exists(f):
            shutil.copyfile(f, os.path.join(p, "critique_gpt.json"))
            print("collected", pid)
        else:
            print("not yet", pid)
        continue
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(p):
        if not name.startswith("critique_"):
            shutil.copyfile(os.path.join(p, name), os.path.join(dst, name))
    json.dump({"action": "delegate", "agent": "codex", "instruction": INSTRUCTION.format(t=t),
               "id": time.strftime("%Y%m%dT%H%M%S")}, open(os.path.join(dst, "request.json"), "w"), indent=1)
    print("request", t)
sys.exit(0)
