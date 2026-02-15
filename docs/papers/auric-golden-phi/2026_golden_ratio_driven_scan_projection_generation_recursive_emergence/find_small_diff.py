#!/usr/bin/env python3
import os

pairs = []
appendix_dir = 'sections/appendix'

for root, dirs, files in os.walk(appendix_dir):
    for file in files:
        if file.endswith('.tex') and not file.endswith('_en.tex'):
            cn_path = os.path.join(root, file)
            en_path = os.path.join(root, file.replace('.tex', '_en.tex'))

            if os.path.exists(en_path):
                with open(cn_path) as f:
                    cn_lines = len(f.readlines())
                with open(en_path) as f:
                    en_lines = len(f.readlines())
                diff = cn_lines - en_lines

                if diff != 0 and abs(diff) <= 30:
                    pairs.append((abs(diff), diff, os.path.basename(cn_path), cn_path, en_path))

pairs.sort()
print(f"共找到 {len(pairs)} 个差异在30行以内的文件:\n")
for abs_diff, diff, name, cn, en in pairs:
    print(f'{abs_diff:3d} ({diff:+3d})  {name}')
    print(f'           CN: {cn}')
    print(f'           EN: {en}')
    print()
