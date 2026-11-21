"""Generate "The Lantern House", an invented 8-episode demo show for the web apps' screenshots and demos.

  python3 samples/make_demo_show.py            # writes samples/The Lantern House/ep01.txt ... ep08.txt

Every line is invented for this repository; there is no Kuku screenplay text here. The show uses the same
screenplay format as the assignment pack, and it plants a few continuity errors on purpose so the
Continuity Checker has something to find:
  - the estate is spelled Harrowgate, Harrogate and Harrowgait in different episodes  (NAME_DRIFT)
  - Mara is labelled MARA in most episodes and LADY MARA in one                       (LABEL_ALIAS)
  - a recurring speaker is only ever called TALL STRANGER                            (UNNAMED_RECURRING)
  - one line has far too many words for its time slot                               (SPEECH_RATE)
  - Episode 6's continuity notes say it follows Episode 4                            (CONTINUITY_REF)
"""

from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent / "The Lantern House"


def stamp(t: float) -> str:
    m = int(t // 60)
    return f"{m:02d}:{t - 60 * m:05.2f}"


def screenplay(n, logline, notes, heading, beats):
    end = max(b[2] for b in beats) + 1
    out = [f"EPISODE NUMBER: Episode {n}", f"EPISODE LOGLINE: {logline}", f"CONTINUITY NOTES: {notes}", "",
           "--- SCRIPT START ---", "", "SCENE 01", f"Scene heading: {heading}", f"Scene start: {stamp(0)}",
           f"Scene end: {stamp(end)}", "", "Actions and dialogue:", ""]
    for label, s, e, text in beats:
        plain = label.split(" (")[0] in ("CAMERA", "ACTION", "SOUND FX")
        out += [f"**{label}:**", f"Start: ({stamp(s)}) | End: ({stamp(e)})", text if plain else f'"{text}"', ""]
    return "\n".join(out + ["--- SCRIPT END ---", ""])


def timed(lines, start=0.0, gap=0.5):
    """lines: (label, seconds, text). Lays cues end to end; CAMERA cues overlap the next line like the pack does."""
    t, out = start, []
    for label, dur, text in lines:
        out.append((label, round(t, 2), round(t + dur, 2), text))
        if not label.startswith("CAMERA"):
            t += dur + gap
    return out


def ep(n, mara="MARA"):
    E = {
        1: ("Mara arrives at Harrowgate to sell her late father's lamps and finds the house expecting her.", "none",
            "INT. HARROWGATE HALL - NIGHT", [
                ("CAMERA", 3, "Wide shot of a hall full of unlit lanterns."),
                (f"{mara} (Tired)", 2.5, "I only came to sell the lamps."),
                ("HOUSEKEEPER BRAND (Polite)", 2.5, "Of course, miss. Tea first."),
                (f"{mara} (Polite)", 2, "Thank you."),
                ("CAMERA", 2, "Close-up on a portrait with Mara's face."),
                (f"{mara} (Shocked, Afraid)", 2.5, "Why is my face on your wall?"),
                ("HOUSEKEEPER BRAND (Cold)", 2.5, "Because you were born in this house."),
                (f"{mara} (Desperate)", 3, "My father said Harrowgate burned before I was born!"),
                ("ACTION", 2, "Every lantern in the hall flickers on at once."),
                ("TALL STRANGER (Menacing)", 3, "Your father lied, and he paid for it."),
                (f"{mara} (Defiant)", 2.5, "Who are you? Show your face!"),
                ("TALL STRANGER (Sinister)", 3, "Ask the lamp in your bag who I am."),
                (f"{mara} (Trembling)", 2.5, "There is nothing in my bag."),
                ("SOUND FX", 2, "Glass cracks inside Mara's satchel."),
                ("TALL STRANGER (Threatening)", 3.5, "Light it before midnight, or the house will take you."),
                ("SOUND FX", 2, "A clock begins to strike."),
                (f"{mara} (Calm)", 2.5, "I will go to bed now."),
                ("HOUSEKEEPER BRAND (Warm)", 2.5, "Your room is ready, miss."),
                (f"{mara} (Soft)", 2, "Good night."),
            ]),
        2: ("Mara lights the cracked lamp and sees the night her mother vanished.", "Picks up directly from Episode 1.",
            "INT. HARROWGATE ATTIC - NIGHT", [
                ("CAMERA", 3, "Mara kneels by a cracked brass lamp."),
                (f"{mara} (Quiet)", 2.5, "One match. That is all."),
                ("SOUND FX", 2, "The wick catches with a hiss."),
                (f"{mara} (Horrified)", 2.5, "Mother? Mother, it's me!"),
                ("ELENA (Afraid, Pleading)", 3, "Mara, run! Don't let Corwin find the key!"),
                (f"{mara} (Desperate)", 2.5, "What key? Where are you?"),
                ("TALL STRANGER (Cold)", 3, "She can't hear you. She never could."),
                (f"{mara} (Furious)", 3, "You took her! You took her from Harrowgate!"),
                ("TALL STRANGER (Sinister)", 3, "I kept her safe. Your uncle wanted her drowned."),
                (f"{mara} (Shocked)", 2, "My uncle is dead."),
                ("TALL STRANGER (Chilling)", 3.5, "Then who signed your letter of invitation?"),
                ("SOUND FX", 2, "The lamp goes dark."),
                (f"{mara} (Shaken)", 2.5, "I need some air."),
                ("HOUSEKEEPER BRAND (Gentle)", 2.5, "The garden is quiet at night."),
                (f"{mara} (Soft)", 2, "Thank you."),
            ]),
        3: ("Uncle Corwin returns, alive, and claims Harrowgate as his own.", "Continues from Episode 2.",
            "INT. HARROWGATE DINING ROOM - DAY", [
                ("CAMERA", 3, "A long table set for two."),
                ("CORWIN (Charming)", 2.5, "Sit, niece. You look pale."),
                (f"{mara} (Wary)", 2.5, "They buried you nine years ago."),
                ("CORWIN (Amused)", 2.5, "They buried a box, Mara."),
                (f"{mara} (Accusing)", 3, "You wrote the letter. You brought me here!"),
                ("CORWIN (Cold)", 3, "I brought you home. Sign the deed and you may leave."),
                (f"{mara} (Defiant)", 2.5, "The deed to Harrowgate is mine."),
                ("CORWIN (Menacing)", 3, "Not if your mother is found alive."),
                ("TALL STRANGER (Low)", 2.5, "Don't sign it. He's lying."),
                ("CORWIN (Furious)", 2.5, "Who let him in here?"),
                (f"{mara} (Shocked)", 2.5, "You can see him too?"),
                ("CORWIN (Sinister)", 3.5, "I see him every night. He's the man I buried."),
                ("SOUND FX", 2, "A glass shatters on the floor."),
                (f"{mara} (Calm)", 2.5, "I will think about the deed."),
                ("CORWIN (Warm)", 2, "Take your time."),
            ]),
        4: ("Mara searches the lamp room for the key and finds her father's diary.", "Follows Episode 3.",
            "INT. HARROGATE LAMP ROOM - NIGHT", [
                ("CAMERA", 3, "Shelves of lamps, each with a paper label."),
                (f"{mara} (Whisper)", 2.5, "Elena. Corwin. Mara. Father labelled us."),
                ("HOUSEKEEPER BRAND (Nervous)", 2.5, "You shouldn't be in here, miss."),
                (f"{mara} (Urgent)", 3, "Then tell me where the key is, Brand."),
                ("HOUSEKEEPER BRAND (Afraid)", 3, "In the diary. But Harrogate keeps what it is given."),
                ("ACTION", 2, "Mara pulls a diary from behind the Mara lamp."),
                (f"{mara} (Reading, Shocked)", 3, "My mother isn't missing. She is inside the lamp."),
                ("TALL STRANGER (Urgent)", 3, "And Corwin has the only flame that frees her."),
                (f"{mara} (Desperate)", 2.5, "Then I'll take it from him."),
                ("TALL STRANGER (Grim)", 4, "If you fail, you take her place in the glass."),
                ("SOUND FX", 2, "Footsteps on the stairs."),
                ("HOUSEKEEPER BRAND (Quiet)", 2.5, "Go to bed, miss. Quickly."),
                (f"{mara} (Soft)", 2, "Good night, Brand."),
            ]),
        5: ("At the lantern feast, Mara tries to steal Corwin's flame.", "Picks up from Episode 4.",
            "INT. HARROWGATE BALLROOM - NIGHT", [
                ("CAMERA", 3, "A ballroom lit by a hundred lanterns."),
                ("LADY MARA (Nervous)", 2.5, "Smile, and keep him talking."),
                ("HOUSEKEEPER BRAND (Whisper)", 2, "The flame is in his ring."),
                ("CORWIN (Charming)", 2.5, "Dance with me, niece."),
                ("LADY MARA (Polite)", 2, "One dance."),
                ("ACTION", 2, "Mara slips the ring from Corwin's finger."),
                ("CORWIN (Furious)", 2.5, "Thief! Seize her!"),
                ("LADY MARA (Defiant)", 3, "You trapped my mother in glass for nine years!"),
                ("CORWIN (Cold, Menacing)", 3.5, "And tonight I will trap her daughter beside her."),
                ("TALL STRANGER (Urgent)", 1.2, "Mara run now to the lamp room before he reaches the stairs and locks every door behind you"),
                ("SOUND FX", 2, "Every lantern in the ballroom goes out."),
                ("LADY MARA (Calm)", 2.5, "I can find my way."),
                ("HOUSEKEEPER BRAND (Warm)", 2, "This way, miss."),
            ]),
        6: ("Mara frees her mother, and the Man in Grey reveals who he is.", "Follows Episode 4.",
            "INT. HARROWGAIT LAMP ROOM - NIGHT", [
                ("CAMERA", 3, "Mara holds the ring over the cracked lamp."),
                (f"{mara} (Breathless)", 2.5, "Come back to me, Mother."),
                ("SOUND FX", 2, "Glass splits from top to bottom."),
                ("ELENA (Weak)", 2.5, "Mara? You've grown so tall."),
                (f"{mara} (Crying, Relieved)", 2.5, "I've got you. I've got you."),
                ("ELENA (Afraid)", 3, "Where is he? Where is the man in grey?"),
                ("TALL STRANGER (Quiet)", 2.5, "Here, Elena. Where I always was."),
                ("ELENA (Shocked)", 2.5, "Thomas? You died in the fire!"),
                (f"{mara} (Stunned)", 2.5, "Father?"),
                ("TALL STRANGER (Grim)", 3.5, "Corwin lit the fire at Harrowgait. And he is outside this door."),
                ("SOUND FX", 2, "The door handle turns slowly."),
                ("ELENA (Calm)", 2.5, "Sit with me a moment."),
                (f"{mara} (Soft)", 2, "Always."),
            ]),
        7: ("Corwin bargains for the house, and Mara learns the price.", "Picks up directly from Episode 6.",
            "INT. HARROWGATE LAMP ROOM - NIGHT", [
                ("CAMERA", 3, "Corwin stands in the doorway with a lantern."),
                ("CORWIN (Smooth)", 2.5, "A family reunion. How touching."),
                (f"{mara} (Defiant)", 2.5, "It's over, Corwin."),
                ("CORWIN (Cold)", 3, "Harrowgate needs a keeper. It always takes one."),
                ("ELENA (Afraid)", 2.5, "Don't listen to him, Mara."),
                ("CORWIN (Menacing)", 3, "Give me the ring, or the house takes your mother back."),
                (f"{mara} (Desperate)", 2.5, "Take me instead!"),
                ("TALL STRANGER (Urgent)", 2.5, "No! That's what he wants!"),
                ("CORWIN (Triumphant)", 3.5, "Then it's agreed. At dawn, the house chooses."),
                ("SOUND FX", 2, "Every clock in the house stops."),
                (f"{mara} (Quiet)", 2.5, "Then we have until dawn."),
                ("ELENA (Gentle)", 2, "Rest, my love."),
            ]),
        8: ("At dawn, the house chooses its keeper.", "Picks up from Episode 7.",
            "EXT. HARROWGATE COURTYARD - DAWN", [
                ("CAMERA", 3, "Grey light over a courtyard of lanterns."),
                (f"{mara} (Resolute)", 2.5, "I'm ready."),
                ("CORWIN (Smug)", 2.5, "Step into the circle, niece."),
                ("TALL STRANGER (Firm)", 2.5, "No. I step in."),
                (f"{mara} (Horrified)", 2.5, "Father, no!"),
                ("TALL STRANGER (Tender)", 3, "I've kept this house for nine years. I can keep it longer."),
                ("CORWIN (Furious)", 2.5, "That's not the bargain!"),
                ("ELENA (Cold)", 3, "The house chooses, Corwin. And it's looking at you."),
                ("ACTION", 2, "The lanterns turn towards Corwin."),
                ("CORWIN (Terrified)", 3.5, "Mara, help me! I'm your blood!"),
                ("SOUND FX", 2, "A single lantern lights by itself."),
                (f"{mara} (Calm)", 2.5, "The sun is up."),
                ("ELENA (Warm)", 2, "Let's go home."),
            ]),
    }[n]
    logline, notes, heading, lines = E
    return screenplay(n, logline, notes, heading, timed(lines))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for n in range(1, 9):
        (OUT / f"ep{n:02d}.txt").write_text(ep(n), encoding="utf-8")
    print(f"wrote 8 episodes to {OUT}")


if __name__ == "__main__":
    main()
