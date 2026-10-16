# Sunday Crazies and related Sunday ride demands — 2026-10-16

Reference: current snapshot ftp_set=300W, updated 2026-10-16T22:40:49.201008. Threshold bins are fixed descriptive reference values, not a new FTP/CP diagnosis.

## Identification and source

The 90-day API activity list was fetched separately for this analysis. Only 2026-08-23 i178739363 is explicitly titled “first crazies is crazy🤪”. All seven Sunday samples below are Sunday by local date. The user reports Crazies every Sunday; individual other titles do not independently name Crazies. 10/08 is a Thursday group ride and is separate context. Raw API details and timestamped power streams: `2026-10-16-crazies-raw/<date>_<id>.json`; each contains GET activity summary/intervals plus GET streams. No source warehouse or vault edits were made.

## Full-ride observed rolling best powers (W)

| Date / ID | 5s | 15s | 30s | 60s | 180s | 300s | 20min |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-23 / i178739363 | 786.6 | 593.9 | 556.7 | 501.9 | 327.2 | 296.6 | 271.1 |
| 2026-08-30 / i181164446 | 609.0 | 472.9 | 434.3 | 402.3 | 331.6 | 318.4 | 286.7 |
| 2026-09-06 / i183730877 | 953.0 | 802.4 | 688.7 | 585.0 | 356.1 | 311.8 | 280.8 |
| 2026-09-13 / i186055900 | 934.2 | 774.4 | 615.5 | 525.6 | 325.5 | 308.8 | 288.9 |
| 2026-09-20 / i188375483 | 1137.0 | 848.0 | 643.6 | 529.8 | 316.6 | 293.6 | 262.7 |
| 2026-10-04 / i193197201 | 580.6 | 452.1 | 406.9 | 379.4 | 342.3 | 324.5 | 295.4 |
| 2026-10-08 / i195102040 | 1014.2 | 804.0 | 529.6 | 384.6 | 343.2 | 335.2 | 231.1 |
| 2026-10-11 / i195955105 | 1078.8 | 804.6 | 700.4 | 572.9 | 349.2 | 311.2 | 272.7 |

These are observed windows in actual rides, not verified all-out tests. Timestamp gaps and missing power cannot be crossed by a rolling window.

## Main portion proxy and repeated bouts

Proxy: remove initial low-power lap (usually ~29–30min recorded) and final clear low-power lap. This is a power/lap-defined analysis cut, not a verified bunch-ride GPS boundary. On 9/13 combine all initial low-power laps before index1710; 8/30 has no clear easy final lap, so its ending is retained. 10/04 is truncated and its title reports being dropped after restarting training; its 25min main proxy is not comparable to a complete Sunday.

| Date | Main min / AP W | Raw >300W | Raw >360W | Raw >450W | >=360W bouts / median gap s | >=450W bouts / median gap s |
|---|---:|---:|---:|---:|---:|---:|
| 2026-08-23 | 86.2 / 233.2 | 27:40 | 16:37 | 5:51 | 50 / 58.0 | 12 / 346.0 |
| 2026-08-30 | 92.4 / 257.2 | 31:34 | 15:58 | 4:06 | 59 / 47.5 | 3 / 996.0 |
| 2026-09-06 | 87.5 / 250.1 | 28:15 | 12:36 | 4:07 | 34 / 105.0 | 7 / 271.0 |
| 2026-09-13 | 83.8 / 266.1 | 32:18 | 17:07 | 6:08 | 58 / 55.0 | 10 / 187.0 |
| 2026-09-20 | 85.7 / 247.5 | 27:01 | 13:18 | 4:25 | 42 / 80.0 | 13 / 228.0 |
| 2026-10-04 | 25.2 / 294.0 | 12:29 | 7:32 | 2:19 | 33 / 26.0 | 4 / 58.0 |
| 2026-10-08 | 68.0 / 233.1 | 23:22 | 6:36 | 1:54 | 19 / 66.0 | 8 / 123.0 |
| 2026-10-11 | 88.6 / 252.4 | 29:30 | 13:48 | 4:33 | 40 / 86.0 | 5 / 913.0 |

Bout definition: centered 5s moving average >=360W or >=450W, qualifying span at least5s, merge dips lasting <=3s within continuous 1Hz recording, retain raw mean >=threshold. Bout counts therefore exclude isolated 1–4s spikes; detected boundaries are approximate (~2s) and are not physical/physiological onset claims. Time-above bins count raw samples with strict > rather than smoothing. Gaps are end-to-start elapsed intervals; they are not proven easy recovery or complete W′ recovery. Detailed bouts, gap power and gaps caused by pauses are in JSON.

## Key evidence

- Explicit Crazies 8/23: full recorded AP215.1W, API weighted average258W. Initial portion AP168W (summary first lap), so full AP dilutes the harder main portion:86.2 recorded min at233.2W,16:37 raw>360W and5:51>450W. At >=360W there are50 defined bouts, median9s, median end-to-start gap58s;25 of49 gaps<=60s. At >=450W there are12 bouts, median7.5s,3>=15s and2>=30s;gap30–1139s. In the final cluster,13s at503.6W is followed after30s at154W by40s at536.8W. Observed best60s501.9W occurs near elapsed7781s, at the end of the ride. Source:8/23 raw stream and JSON main.bouts / full.peaks.
- Related Sunday10/11: full AP228.2W, API weighted average275W; initial portion AP171W. Main88.6 recorded min at252.4W,29:30 raw>300W,13:48>360W and4:33>450W. >=360W:40 defined bouts, median7.5s,median gap86s,17/39 gaps<=60s. >=450W:5 defined bouts;three longer late bouts43s at644.5W (elapsed5866s),22s at718W (6188s),34s at669.3W (7495s). First pair separated by279s with average247.4W;last bout occurs about125min after start. These are smoothed-threshold segments inside longer efforts, not whole attacks. Source:10/11 raw stream and JSON main.bouts.
- Across the six complete related Sunday samples8/23,8/30,9/6,9/13,9/20,10/11:main proxy83.8–92.4 recorded min,AP233.2–266.1W;34–59 bouts>=360W and3–13 bouts>=450W using the stated algorithm. Counts differ materially by threshold and ride. This describes recorded exposure, not a universal Singapore race demand.
- Conditions:API activity average device temperature27.1°C (8/23,range24–31) and27.5°C (10/11,25–30). These are recorded sensor temperatures, not verified ambient weather/humidity. October13 title about haze/humidity is not evidence that either Sunday had identical conditions.

## Interpretation and limits

The traces support a repeated-acceleration requirement:many5–15s harder changes, occasional30–60s strong efforts, and ability to produce them late after sustained riding. A single fresh5s maximum does not summarize this task. Conversely, the traces do not demonstrate that threshold is unimportant or that making threshold work a minority is always optimal. Sustained background power and the workload between large bursts are substantial; aerobic contribution/recovery and a training prescription require additional evidence. No CP/W′ fit, anaerobic-energy estimate, or causal conclusion is made.

The10/04 “dropped” title plus25min main294W is relevant context for sustained tolerance, but it does not establish whether limitation came from endurance, post-crash recovery, positioning or tactics. No prescription or entire training plan is produced here.

## Verification / integrity pass

All quantitative claims above were computed from the cited raw activity streams or read from that activity’s fresh API summary. ftp_set is from live snapshot. All rolling windows were checked against exact slices and timestamps. No invented effort labels, maximal-test anchors, energy-system partition or external race generalization. Source records remain available in the analysis raw subdirectory.
