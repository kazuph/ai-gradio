#!/bin/bash
set -euo pipefail

# Parse .dev.vars and set secrets
if [[ ! -f .dev.vars ]]; then
    echo "File .dev.vars not found!"
    exit 1
fi
while IFS='=' read -r name value
do
  # コメント行をスキップ
  [[ $name =~ ^#.*$ ]] && continue
  # 空行をスキップ
  [[ -z $name ]] && continue
  # valueの前後のクオートを削除
  value=$(echo $value | sed -e 's/^"//' -e 's/"$//')
  echo "Setting $name" #: $value"
  echo $value | npx wrangler secret put "$name"
done < .dev.vars

pnpm run deploy
