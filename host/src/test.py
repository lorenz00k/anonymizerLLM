from piifilter.detection.llm import llm_find

text = (
    "Kannst du mir helfen eine interne Ankündigung zu schreiben? "
    "Projekt Phoenix launcht jetzt doch erst im Q3 2027 statt wie geplant im Q1, "
    "das darf noch nicht nach außen dringen."
)

print("Rufe Ollama auf...")
matches = llm_find.find_matches(text, chat_id="debug")
print(f"{len(matches)} Match(es):")
for m in matches:
    print(f"  - {m}")
print("Fertig.")