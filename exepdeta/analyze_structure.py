import csv

files = ['3_1.csv', '3_2-6.csv', '4_1-5.csv', 'file.csv', 'file2.csv', 'file3.csv']

for fname in files:
    print(f'===== {fname} =====')
    trials = {}
    total_lines = 0
    all_disp = []
    all_force = []

    with open(fname, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f)
        header = next(reader)
        print(f'Header: {header}')
        for row in reader:
            total_lines += 1
            trial = int(row[0])
            time_val = float(row[1])
            disp = float(row[2])
            force = float(row[3])
            all_disp.append(disp)
            all_force.append(force)
            if trial not in trials:
                trials[trial] = {
                    'count': 0, 'min_disp': disp, 'max_disp': disp,
                    'min_force': force, 'max_force': force,
                    'min_time': time_val, 'max_time': time_val,
                    'start_line': total_lines + 1
                }
            t = trials[trial]
            t['count'] += 1
            t['min_disp'] = min(t['min_disp'], disp)
            t['max_disp'] = max(t['max_disp'], disp)
            t['min_force'] = min(t['min_force'], force)
            t['max_force'] = max(t['max_force'], force)
            t['min_time'] = min(t['min_time'], time_val)
            t['max_time'] = max(t['max_time'], time_val)
            t['end_line'] = total_lines + 1

    print(f'Total data lines: {total_lines} (+ 1 header = {total_lines + 1} total)')
    print(f'Overall displacement range: [{min(all_disp):.6f}, {max(all_disp):.6f}] mm')
    print(f'Overall force range: [{min(all_force):.6f}, {max(all_force):.6f}] N')
    print(f'Number of trials: {len(trials)}')
    for t_num in sorted(trials.keys()):
        t = trials[t_num]
        print(f'  Trial {t_num}: {t["count"]} rows, lines {t["start_line"]}-{t["end_line"]}')
        print(f'    Time: [{t["min_time"]:.2f}, {t["max_time"]:.2f}] sec')
        print(f'    Displacement: [{t["min_disp"]:.6f}, {t["max_disp"]:.6f}] mm')
        print(f'    Force: [{t["min_force"]:.6f}, {t["max_force"]:.6f}] N')
    print()

# Now analyze force patterns - find peaks and oscillation
print('===== FORCE PEAK ANALYSIS =====')
for fname in files:
    print(f'\n--- {fname} ---')
    with open(fname, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f)
        next(reader)
        data = []
        for row in reader:
            data.append((int(row[0]), float(row[1]), float(row[2]), float(row[3])))

    # Find where force peaks occur per trial
    current_trial = None
    trial_data = []
    for trial, time_val, disp, force in data:
        if trial != current_trial:
            if trial_data:
                forces = [d[3] for d in trial_data]
                max_f = max(forces)
                max_idx = forces.index(max_f)
                max_disp = trial_data[max_idx][2]
                # Check for oscillation: count sign changes in force derivative
                sign_changes = 0
                for i in range(2, len(forces)):
                    d1 = forces[i-1] - forces[i-2]
                    d2 = forces[i] - forces[i-1]
                    if d1 * d2 < 0:
                        sign_changes += 1
                print(f'  Trial {current_trial}: peak force={max_f:.6f}N at disp={max_disp:.4f}mm, oscillation sign changes={sign_changes}')
            current_trial = trial
            trial_data = []
        trial_data.append((trial, time_val, disp, force))

    # Last trial
    if trial_data:
        forces = [d[3] for d in trial_data]
        max_f = max(forces)
        max_idx = forces.index(max_f)
        max_disp = trial_data[max_idx][2]
        sign_changes = 0
        for i in range(2, len(forces)):
            d1 = forces[i-1] - forces[i-2]
            d2 = forces[i] - forces[i-1]
            if d1 * d2 < 0:
                sign_changes += 1
        print(f'  Trial {current_trial}: peak force={max_f:.6f}N at disp={max_disp:.4f}mm, oscillation sign changes={sign_changes}')

# Analyze the force curve shape - when does force start rising, peak, then drop?
print('\n===== FORCE CURVE SHAPE (phase analysis) =====')
for fname in files:
    print(f'\n--- {fname} ---')
    with open(fname, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f)
        next(reader)
        data = []
        for row in reader:
            data.append((int(row[0]), float(row[1]), float(row[2]), float(row[3])))

    current_trial = None
    trial_data = []
    for trial, time_val, disp, force in data:
        if trial != current_trial:
            if trial_data:
                forces = [d[3] for d in trial_data]
                disps = [d[2] for d in trial_data]
                # Find where force first exceeds 0.02N threshold
                rise_disp = None
                for i, f in enumerate(forces):
                    if f > 0.02:
                        rise_disp = disps[i]
                        break
                # Find peak
                max_f = max(forces)
                max_idx = forces.index(max_f)
                peak_disp = disps[max_idx]
                # Find where force drops below 0.02N after peak
                drop_disp = None
                for i in range(max_idx, len(forces)):
                    if forces[i] < 0.02:
                        drop_disp = disps[i]
                        break
                print(f'  Trial {current_trial}: rise@{rise_disp}mm, peak={max_f:.4f}N@{peak_disp:.4f}mm, drop@{drop_disp}mm, end_disp={disps[-1]:.4f}mm')
            current_trial = trial
            trial_data = []
        trial_data.append((trial, time_val, disp, force))
    if trial_data:
        forces = [d[3] for d in trial_data]
        disps = [d[2] for d in trial_data]
        rise_disp = None
        for i, f in enumerate(forces):
            if f > 0.02:
                rise_disp = disps[i]
                break
        max_f = max(forces)
        max_idx = forces.index(max_f)
        peak_disp = disps[max_idx]
        drop_disp = None
        for i in range(max_idx, len(forces)):
            if forces[i] < 0.02:
                drop_disp = disps[i]
                break
        print(f'  Trial {current_trial}: rise@{rise_disp}mm, peak={max_f:.4f}N@{peak_disp:.4f}mm, drop@{drop_disp}mm, end_disp={disps[-1]:.4f}mm')
