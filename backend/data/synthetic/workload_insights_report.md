# Workload Insights Report — Study Capacity Analysis 2026
_Synthetic document — all data is illustrative and does not correspond to real employees, calendars, or productivity records._

## Overview

This report analyses the relationship between engineering workload patterns and certification study effectiveness. Data covers Team A members across a 16-week observation window (Q1–Q2 2026). Calendar signals are synthetic proxies for meeting load, sprint boundaries, and on-call rotations.

## Meeting Hours vs Study Completion Rate

Correlation analysis between weekly meeting hours and the percentage of planned study sessions completed that week.

| Weekly Meeting Hours | Avg Study Session Completion Rate | Sample Weeks |
|---|---|---|
| < 8 h/week | 88% | 22 weeks |
| 8–12 h/week | 74% | 31 weeks |
| 13–16 h/week | 58% | 18 weeks |
| > 16 h/week | 34% | 9 weeks |

**Finding**: Completion rate drops sharply when weekly meeting hours exceed 12 hours. Learners with > 16 h/week of meetings complete fewer than 1 in 3 planned study sessions.

**Recommendation**: Flag learners whose calendar shows > 12 h/week of meetings and proactively shorten study sessions from 90 minutes to 45-minute focused blocks during high-meeting weeks.

## Sprint-Cycle Impact on Study Streaks

Team A follows 2-week sprints. Streak data was segmented by sprint phase.

| Sprint Phase | Avg Daily Study Minutes | Streak Break Probability |
|---|---|---|
| Sprint start (days 1–3) | 42 min | 8% |
| Sprint mid (days 4–8) | 38 min | 12% |
| Sprint end / sprint close (days 9–10) | 18 min | 41% |
| Between sprints (retrospective + planning day) | 9 min | 67% |

**Finding**: Sprint close and the inter-sprint transition day account for 61% of all streak breaks in the observation window. Learners frequently skip study entirely on sprint close and planning days.

**Recommendation**: Reduce the study target on sprint close days to a 15-minute minimum maintenance session (flashcard review or single practice question) to preserve streak continuity without adding cognitive load.

## On-Call Rotation Impact

Team A members rotate on-call shifts weekly. On-call weeks were identified from calendar data.

| Metric | On-Call Week | Non-On-Call Week |
|---|---|---|
| Avg study hours | 1.8 h | 5.9 h |
| Study session completion rate | 31% | 79% |
| Streak break rate | 55% | 9% |
| Practice test attempts | 0.2 / week | 1.4 / week |

**Finding**: On-call weeks represent the single largest predictor of streak breaks. Learners are effectively unable to maintain normal study pace during on-call rotations.

**Recommendation**: Automatically suspend study targets (and pause exam countdown timers) during confirmed on-call weeks. Resume with a ramp-up schedule (50% of normal pace) in the first 3 days post-on-call.

## Recommended Calendar Patterns for High-Workload Periods

### Pattern 1: Meeting-Heavy Weeks (> 12 h meetings)
- Shorten individual sessions from 90 min to two 30-min blocks (morning + evening)
- Prioritise weak-area flashcard review over new content consumption
- Do not schedule practice exams during meeting-heavy weeks
- If streak is > 14 days, allow one planned rest day without streak penalty

### Pattern 2: Sprint Close / Planning Days
- Minimum viable session: 15 minutes (counts toward streak)
- Suggested activity: single-domain review quiz (10 questions)
- Avoid new module starts on these days
- Auto-reschedule any missed lab sessions to the following sprint mid-period

### Pattern 3: On-Call Weeks
- Suspend study plan; mark week as "protected" in the learning calendar
- Send a single daily micro-reminder (1 concept card, < 2 min) to maintain cognitive context
- Resume full plan on day 1 post-on-call with a 3-day ramp (50% → 75% → 100%)

### Pattern 4: High-Readiness Periods (> 30 consecutive streak days, practice avg ≥ 75%)
- Consider scheduling the exam 3–4 weeks out to capitalise on peak readiness
- Shift from new content to practice test repetition (2–3 full exams in the final 2 weeks)
- Reduce study hours by 20% in the final week to avoid burnout

## Optimal Study Time Windows (Team A Aggregate)

Based on session performance scores by time-of-day:

| Time Window | Avg Practice Score | Session Completion Rate | Notes |
|---|---|---|---|
| 07:00–09:00 | 74% | 82% | Morning learners score highest |
| 12:00–13:00 | 68% | 71% | Lunchtime sessions are shorter but consistent |
| 18:00–20:00 | 71% | 77% | Evening sessions are the most common |
| 21:00–23:00 | 62% | 58% | Late-night sessions show lower scores and more drop-offs |

**Recommendation**: Personalise study reminders to each learner's stated preferred study time. Avoid auto-scheduling sessions in the 21:00–23:00 window for learners with a history of late-night drop-offs.
