# Question prompt

Every evaluated MLLM receives the same system prompt in every setting.

```text
You are an expert in display ergonomics and human factors. Each question shows a user interface as it appears on a specific display and viewing condition. Answer with the letter of the correct option only.
```

The user prompt states the display condition, the requirement, the question and the options. The exact user prompt of every question in S0, S1 and S2 is stored in `data/questions.jsonl` under `prompts`. Example for question `q00075` (boundary contrast, desktop, estimation):

**S0**

```text
Display: the interface is shown on a 24-inch 1920x1080 desktop monitor (92 ppi), viewed at 600 mm and operated with a mouse.
Requirement: the visual boundary of an interactive control must reach at least 3.0:1 contrast against the adjacent background.
Question: Which range best describes the highlighted control's boundary contrast?
Options:
(A) below 2:1
(B) 2:1 to 3:1
(C) 3:1 or higher
Answer with a single letter (A/B/C).
```

**S1** adds the line

```text
Image 2 is a magnified view of the highlighted region(s) for close inspection.
```

**S2** adds the measured value

```text
Measured: boundary contrast 2.65:1.
```
