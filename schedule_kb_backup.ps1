# KB daily backup
Write-Host backup_start
date
python D:/hermes-tools/scripts/backup_kb.py export
Write-Host backup_done
