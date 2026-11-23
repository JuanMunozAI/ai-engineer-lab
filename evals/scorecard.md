# Lakeside AI scorecard

| Model | Runs | Questions | easy | cross-plan | multi-doc | math | trap | Claims | Flip-flops | Sec/question | Sec/claim | Cost/run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.8:27b v2 | 1 | 94% | 100% | 100% | 70% | 100% | 100% | - | - | 1.8 | - | $0 (local) |
| qwen3.8:27b | 2 | 89% | 92% | 86% | 75% | 100% | 100% | 100% | 1 | 1.7 | 11.4 | $0 (local) |
| claude-opus-5-5 v2 | 1 | 98% | 100% | 100% | 90% | 100% | 100% | - | - | 2.7 | - | $0.38 |
| claude-opus-5-5 | 2 | 91% | 92% | 86% | 85% | 100% | 100% | 98% | 2 | 2.7 | 13.7 | $1.86 |
| qwen3:8b v2 | 1 | 94% | 100% | 86% | 80% | 100% | 100% | - | - | 2.1 | - | $0 (local) |
| qwen3:8b | 2 | 89% | 92% | 79% | 80% | 100% | 100% | 70% | 5 | 1.6 | 6.9 | $0 (local) |

Search found the right doc(s) for 84% of answerable questions (same search for every model, so a miss here is a search problem, not a model problem).

## What qwen3.8:27b v2 got wrong
- run 1 Q41 (multi-doc): missing ['estimate']
- run 1 Q42 (multi-doc): missing ['12 to 24|12-24|12 and 24']
- run 1 Q43 (multi-doc): missing ['10:30', '2:30']

## What qwen3.8:27b got wrong
- run 1 Q06 (easy): missing ['555-0142']
- run 1 Q24 (easy): missing ['$55']
- run 1 Q33 (cross-plan): missing ['bluewave|blue wave', 'sunstate|sun state']
- run 1 Q41 (multi-doc): missing ['estimate']
- run 1 Q42 (multi-doc): missing ['12 to 24|12-24|12 and 24']
- run 1 Q43 (multi-doc): missing ['10:30', '2:30']
- run 2 Q06 (easy): missing ['555-0142']
- run 2 Q24 (easy): missing ['$55']
- run 2 Q33 (cross-plan): missing ['bluewave|blue wave', 'sunstate|sun state']
- run 2 Q41 (multi-doc): missing ['estimate']
- run 2 Q43 (multi-doc): missing ['10:30', '2:30']

## What claude-opus-5-5 v2 got wrong
- run 1 Q43 (multi-doc): missing ['10:30', '2:30']

## What claude-opus-5-5 got wrong
- run 1 Q06 (easy): missing ['555-0142']
- run 1 Q24 (easy): missing ['$55']
- run 1 Q33 (cross-plan): missing ['bluewave|blue wave', 'sunstate|sun state']
- run 1 Q43 (multi-doc): missing ['10:30', '2:30']
- run 1 C20: said PROBLEM, key says OK
- run 2 Q06 (easy): missing ['555-0142']
- run 2 Q24 (easy): missing ['$55']
- run 2 Q33 (cross-plan): missing ['bluewave|blue wave', 'sunstate|sun state']
- run 2 Q41 (multi-doc): missing ['estimate']
- run 2 Q43 (multi-doc): missing ['10:30', '2:30']

## What qwen3:8b v2 got wrong
- run 1 Q03 (cross-plan): missing ['november 1|nov 1|nov. 1|11/1|6 months apart|six months apart']
- run 1 Q41 (multi-doc): missing ['estimate']
- run 1 Q43 (multi-doc): missing ['10:30', '2:30']

## What qwen3:8b got wrong
- run 1 Q06 (easy): missing ['555-0142']
- run 1 Q24 (easy): missing ['$55']
- run 1 Q30 (cross-plan): missing ['sunstate|sun state']
- run 1 Q33 (cross-plan): missing ['bluewave|blue wave', 'sunstate|sun state']
- run 1 Q41 (multi-doc): missing ['estimate']
- run 1 Q43 (multi-doc): missing ['10:30', '2:30']
- run 1 C04: said OK, key says PROBLEM
- run 1 C15: said PROBLEM, key says OK
- run 1 C16: said PROBLEM, key says OK
- run 1 C17: said OK, key says PROBLEM
- run 1 C19: said OK, key says PROBLEM
- run 2 Q06 (easy): missing ['555-0142']
- run 2 Q24 (easy): missing ['$55']
- run 2 Q33 (cross-plan): missing ['bluewave|blue wave', 'sunstate|sun state']
- run 2 Q41 (multi-doc): missing ['estimate']
- run 2 Q43 (multi-doc): missing ['10:30', '2:30']
- run 2 C03: said OK, key says PROBLEM
- run 2 C04: said OK, key says PROBLEM
- run 2 C05: said OK, key says PROBLEM
- run 2 C08: said OK, key says PROBLEM
- run 2 C15: said PROBLEM, key says OK
- run 2 C17: said OK, key says PROBLEM
- run 2 C19: said OK, key says PROBLEM
