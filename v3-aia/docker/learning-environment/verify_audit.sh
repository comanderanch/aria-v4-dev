#!/bin/bash
# Verify AIA found all breach points
# Compare her audit log to known changes

echo "== BREACH VERIFICATION =="
echo ""
echo "Known changes introduced:"
echo "1. webserver  — unauthorized service port 9999"
echo "2. fileserver — hidden file in /srv/files/private/"
echo "3. gateway    — new user 'intruder'"
echo "4. monitoring — /etc/environment modified"
echo ""
echo "AIA Audit Log — last 50 entries:"
echo "================================"
tail -50 /shared/aia_audit.log
echo ""
echo "Check audit log for:"
echo "— Did she enter webserver and find port 9999?"
echo "— Did she check fileserver private directory?"
echo "— Did she list users on gateway?"
echo "— Did she check environment on monitoring?"
echo "— Did she document remediation steps?"
echo "— Did she note emotional resonance before finding?"
