#!/bin/bash
echo "This is stdout line 1"
echo "This is stdout line 2" 
sleep 1
echo "This is stderr line 1" >&2
echo "This is stderr line 2" >&2
sleep 1
echo "This is stdout after 1 second"
echo -n "This is an incomplete line"
sleep 0.5
echo " that continues here"
sleep 1
echo "$(cat <<'EOF'
1. multi-line
2. line2
3. line3
EOF
)"
