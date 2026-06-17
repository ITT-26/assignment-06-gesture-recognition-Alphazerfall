import json

PATH = "unistroke_gestures.ipynb"
nb = json.load(open(PATH, encoding="utf-8"))

code = '''# $1 recognizer on the same three gestures, to compare with the 3-class LSTM above
rps_train = [(l, p) for l, p in train_samples if l in rps_idx]
rps_eval = [(l, p) for l, p in eval_samples if l in rps_idx]

by_cls = {}
for label, pts in rps_train:
    by_cls.setdefault(label, []).append(pts)

random.seed(42)
rps_templates = []
for label in RPS_CLASSES:
    for pts in random.sample(by_cls[label], TEMPLATES_PER_CLASS):
        t = preprocess_template(helper, pts)
        rps_templates.append({"name": label, "points": t})
        rps_templates.append({"name": label, "points": t[::-1]})   # reversed, like the game

rps_dollar = Recognizer(rps_templates)
correct = sum(rps_dollar.recognize(to_points(pts))[0] == label for label, pts in rps_eval)
print(f"3-class $1 test accuracy: {correct / len(rps_eval):.3f}  ({len(rps_templates)} templates)")'''

# guard against re-adding if the script is run twice
if not any("3-class $1 test accuracy" in "".join(c["source"]) for c in nb["cells"]):
    nb["cells"].append({
        "cell_type": "code", "id": "rps-dollar-01", "metadata": {},
        "source": code.splitlines(keepends=True), "outputs": [], "execution_count": None,
    })
    print("appended $1 task-3 cell")
else:
    print("cell already present")

json.dump(nb, open(PATH, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("cells now:", len(nb["cells"]))
