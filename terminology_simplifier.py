import re
import json
from pathlib import Path
from nltk.tokenize import RegexpTokenizer
from nltk.stem import WordNetLemmatizer

dictionary_path = Path(__file__).parent / "medical_dictionary.json"

with open(dictionary_path, "r", encoding="utf-8") as file:
    MEDICAL_DICTIONARY = json.load(file)

tokenizer = RegexpTokenizer(r"\b\w+\b")
lemmatizer = WordNetLemmatizer()


def tokenize_text(text):
    return tokenizer.tokenize(text)


def lemmatize_text(tokens):
    return [
        lemmatizer.lemmatize(token.lower())
        for token in tokens
    ]


def normalize_term(text):
    return " ".join(lemmatize_text(tokenize_text(text)))


NORMALIZED_DICTIONARY = {
    normalize_term(term): meaning
    for term, meaning in MEDICAL_DICTIONARY.items()
}


def simplify_medical_text(text):

    tokens = tokenize_text(text)
    lemmatized_tokens = lemmatize_text(tokens)

    identified_terms = []
    detected = set()
    replacements = []

    matches = list(re.finditer(r"\b\w+\b", text))

    max_words = max(
        len(term.split())
        for term in NORMALIZED_DICTIONARY
    )

    i = 0

    while i < len(matches):

        found = False

        for length in range(
            min(max_words, len(matches) - i), 0, -1
        ):

            start = matches[i].start()
            end = matches[i + length - 1].end()

            original_term = text[start:end]

            if not re.fullmatch(
                r"\w+(?:[ \t]+\w+)*", original_term
            ):
                continue

            normalized = normalize_term(original_term)

            if normalized in NORMALIZED_DICTIONARY:

                meaning = NORMALIZED_DICTIONARY[normalized]

                replacement = f"{original_term} ({meaning})"

                replacements.append(
                    (start, end, replacement)
                )

                if normalized not in detected:

                    identified_terms.append({
                        "term": original_term,
                        "meaning": meaning
                    })

                    detected.add(normalized)

                i += length
                found = True
                break

        if not found:
            i += 1

    simplified_text = text

    for start, end, replacement in reversed(replacements):

        simplified_text = (
            simplified_text[:start]
            + replacement
            + simplified_text[end:]
        )

    return {
        "original_text": text,
        "simplified_text": simplified_text,
        "identified_terms": identified_terms,
        "total_terms": len(identified_terms),
        "tokens": tokens,
        "lemmatized_tokens": lemmatized_tokens
    }


if __name__ == "__main__":

    text = input("Enter medical text: ")

    result = simplify_medical_text(text)

    print("\nOriginal Text:")
    print(result["original_text"])

    print("\nTokenization:")
    print(result["tokens"])

    print("\nLemmatization:")
    print(result["lemmatized_tokens"])

    print("\nIdentified Medical Terms:")

    for item in result["identified_terms"]:
        print(item["term"], "->", item["meaning"])

    print("\nSimplified Text:")
    print(result["simplified_text"])

    print("\nTotal Medical Terms:", result["total_terms"])