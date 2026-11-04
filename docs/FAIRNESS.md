[← Back to the README](../README.md)

# How fairness works

Next to a person's points, the panel shows their **fair share** ("fair: 1.15") under "Points this month" (overview) and in the
statistics. This is **not** "everyone gets the same amount", but the share that is due to the person according to their
**load capacity** and their **days present** in the period. Equal points therefore do not mean equal fair shares.

**Calculation**

1. A person's capacity = load capacity (full 1.0 · half 0.5 · paused 0) × number of days present in the period.
   Absences (one-off, fixed weekdays, weekly rhythm, recurring) reduce the days.
2. Fair share = total points of all people × the person's capacity ÷ sum of all capacities.
3. Points of an assignment: completed on time counts in full; late and missed ("Stays undone" included) count with the
   factor from the settings (default: late 1.0, missed 0). Open and swapped assignments do not count in the statistics
   yet, but count fully as load when drawing.
4. The period of the statistics is whole calendar months **up to today**; when drawing, the fairness window applies
   (default 30 days, adjustable in the settings).

**Example 1: everyone completes exactly 1 point, yet the fair shares differ**

It is Tuesday, 3 November. The "month" period therefore covers only Sunday, Monday and Tuesday. Five people have
each completed a task worth 1 point (5 points in total):

| Person | Presence | Days | Fair share | Points |
|---|---|---|---|---|
| Toni | always | 3 | 5 × 3 ÷ 13 = **1.15** | 1 |
| Andrea | always | 3 | **1.15** | 1 |
| Fabian | every 2 weeks Fri–Fri, present right now | 3 | **1.15** | 1 |
| Felix | not Sat and Sun | 2 (Mon, Tue) | 5 × 2 ÷ 13 = **0.77** | 1 |
| Laurenz | not Sat, Sun, Wed | 2 (Mon, Tue) | **0.77** | 1 |

The sum of the days is 13. Whoever is around on fewer days has less claim to tasks, so 1 point is **above** the fair share
for Felix and Laurenz. This evens out with every day, because capacity only grows on days present.
Fabian is only on par with Toni and Andrea as long as his presence phase covers the whole period. In his
week of absence his fair share drops.

**Example 2: half load capacity**

A month with 30 days, Anna (full) and Ben (half) are always present: capacity Anna 30, Ben 15. With 9 points in total,
Anna is due 9 × 30 ÷ 45 = **6** and Ben 9 × 15 ÷ 45 = **3** points. If each person has 4.5 points, Ben is above his
share and Anna below.

**Example 3: late and missed**

A task worth 2 points is completed late. If the "late" factor is set to 0.5, the person is credited 1
point; for "missed" (default 0) they get 0.

**Effect on the draw**

Whoever is below their fair share gets a bigger slice on the wheel. The weight is
`w = f × exp((f − a) ÷ f)` with the fair share `f` and the actual share `a` (the person's points ÷ points of
everyone), then limited to at least 0.5 % and at most 100 % and normalized to chances. Example: Anna and Ben are
both fully capable and always present (`f` = 50 %), Anna has 3 and Ben 1 point in the window (`a` = 75 % and 25 %). Then
Anna's weight is 0.50 × e^−0.5 ≈ 0.30 and Ben's is 0.50 × e^0.5 ≈ 0.82. Ben thus has about a 73 % chance, Anna about 27 %.
Without points in the window, everyone's chance is their fair share; people without capacity (paused or never present in the window) keep only the minimum weight of 0.5 %.

**Further indicators**

- **Fairness index** (statistics): 100 % means everyone has exactly their fair share; it falls with the sum of the
  deviations (index = 1 − ½ × Σ|points − fair share| ÷ total points).
- **Lucky one** is furthest below their fair share, **unlucky one** furthest above; both only with a real
  deviation and from two people on.
