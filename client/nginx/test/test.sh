#!/bin/bash
set -e
function onError () {
  echo "ERROR happened. Quitting..."
  exit 1
}
trap 'onError' ERR
DIR="$(dirname "$(readlink -f "$0")")" && cd "$DIR"

URL="http://localhost:8081/varda"
USER=$(cat $DIR/backend.conf | grep '$auth_user' | awk '{print $3}' | cut -d"'" -f2)
PASS=$(cat $DIR/backend.conf | grep '$auth_pass' | awk '{print $3}' | cut -d"'" -f2)
TOKEN=$(cat $DIR/backend.conf | grep '$auth_token' | awk '{print $3}' | cut -d"'" -f2)

FE_IMAGE="varda-test-frontend-with-lua-str"
BE_INSTANCE="varda-test-backend-mock"
FE_INSTANCE="varda-test-frontend"

docker stop $BE_INSTANCE || echo 'Backend not running'
docker stop $FE_INSTANCE || echo 'Frontend not running'
docker rm $BE_INSTANCE || echo 'Backend not existing'
docker rm $FE_INSTANCE || echo 'Frontend not existing'

function stripFile () {
  local FILE="$1"
  local SSTART="$2"
  local SEND="$3"
  local START=1
  local END=0
  if [ ! -z "$SSTART" ]; then
    START=$(cat "$FILE" | grep -n "$SSTART" | cut -d':' -f 1)
    START=$((START+1))
  fi
  if [ -z "$SEND" ]; then
    END=$(cat "$FILE" | wc -l)
  else
    END=$(cat "$FILE" | grep -n "$SEND" | cut -d':' -f 1)
    END=$((END-1))
  fi
  echo -n "" > "$FILE.tmp"
  cat "$FILE" | awk "NR >= $START && NR <= $END" >> "$FILE.tmp"
  rm "$FILE"
  mv "$FILE.tmp" "$FILE"
}

echo "Generating Dockerfile for frontend container..."
cp $DIR/../../Dockerfile /tmp/FrontendTestDockerfile1
cp $DIR/../../Dockerfile /tmp/FrontendTestDockerfile2
stripFile "/tmp/FrontendTestDockerfile1" "^# Stage 1" "^COPY --from="
stripFile "/tmp/FrontendTestDockerfile2" "^COPY --from=" ""
cat /tmp/FrontendTestDockerfile1 /tmp/FrontendTestDockerfile2 >> /tmp/FrontendTestDockerfile
rm -f /tmp/FrontendTestDockerfile1 /tmp/FrontendTestDockerfile2

echo "Building the frontend container..."
(cd $DIR/../../ && docker build \
    -f /tmp/FrontendTestDockerfile \
    -t $FE_IMAGE .)
rm -f /tmp/FrontendTestDockerfile

echo "Starting frontend test instance..."
docker run -it -d --rm \
  -v $DIR/index.html:/usr/share/nginx/html/index.html \
  -e VARDA_SESSION_SECURE='' \
  -e VARDA_BACKEND_PROTOCOL='http' \
  -e VARDA_BACKEND_HOSTNAME='127.0.0.1:8082' \
  -e VARDA_SALT='testsalt' \
  --name $FE_INSTANCE \
  -p 8081:8080 \
  $FE_IMAGE

echo "Starting backend mock instance..."
docker run -it -d --rm \
  --network container:$FE_INSTANCE \
  -v $DIR/backend.conf:/etc/nginx/conf.d/default.conf \
  --name $BE_INSTANCE \
  $FE_IMAGE

echo "Sleeping for a bit..."
sleep 1
echo "Starting tests..."

FAILED=0
TOTAL=0

function print_header() {
    local DATA="$1"
    local TITLE=$(printf '%s' "$DATA" | head -n 1)
    local REQUEST=$(printf '%s' "$DATA" | head -n 2 | tail -n 1)
    echo ""
    echo "##"
    echo "# $TITLE"
    echo "# $REQUEST"
    echo "##"
    echo ""
}

function dump_data() {
    local DATA="$1"
    echo ""
    echo "### RAW DATA ###"
    echo ""
    echo "$DATA"
}

function execute_request() {
    local TITLE="$1"
    local METHOD="$2"
    local URL="$3"
    local AUTH="$4"
    local COOKIE="$5"
    local DATA=""
    if [ ! -z "$AUTH" ] && [ ! -z "$COOKIE" ]; then
      DATA=$(curl --http1.1 -i -s --cookie "$COOKIE" -H "Authorization: $AUTH" -X$METHOD "$URL")
    elif [ ! -z "$AUTH" ]; then
      DATA=$(curl --http1.1 -i -s -H "Authorization: $AUTH" -X$METHOD "$URL")
    elif [ ! -z "$COOKIE" ]; then
      DATA=$(curl --http1.1 -i -s --cookie "$COOKIE" -X$METHOD "$URL")
    else
      DATA=$(curl --http1.1 -i -s -X$METHOD "$URL")
    fi
    printf '%s\n%s\n%s' "TITLE: $TITLE" "$METHOD $URL HTTP/1.1" "$DATA"
}

function test_status() {
    local DATA="$1"
    local EXP="$2"
    local ROW=$(printf '%s' "$DATA" | grep '^HTTP/1.1')
    local STATUS=$(printf '%s' "$ROW" | awk '{print $2}')
    local RETVAL=1
    ((TOTAL=TOTAL+1))
    if [ "$STATUS" -eq "$EXP" ]; then
      echo "Status expected ($EXP)"
      RETVAL=0
    else
      >&2 echo "Status not expected ($STATUS vs. $EXP)"
      dump_data "$DATA"
      ((FAILED=FAILED+1))
    fi
    return $RETVAL
}

function test_cookie() {
    local DATA="$1"
    local EXP="$2"
    local ROW=$(printf '%s' "$DATA" | grep -o -E 'Set\-Cookie\: .*?;Expires=.{27}')
    local STATUS=$(printf '%s' "$ROW" | cut -d'=' -f2)
    local RETVAL=1
    local COOKIESTATE=""
    ((TOTAL=TOTAL+1))
    if [ -z "$ROW" ]; then
      COOKIESTATE="missing"
    fi
    if [ "${STATUS:0:1}" == ";" ]; then
      COOKIESTATE="empty"
    elif [ -z "$COOKIESTATE" ]; then
      COOKIESTATE="exists"
    fi
    if [ "$COOKIESTATE" == "$EXP" ]; then
      echo "Cookie expected ($EXP)"
      RETVAL=0
    else
      >&2 echo "Cookie not expected (Expected: $EXP, Got: $COOKIESTATE)"
      dump_data "$DATA"
      ((FAILED=FAILED+1))
    fi
    return $RETVAL
}

function test_content() {
    local DATA="$1"
    local TEST="$2"
    local WHAT="$3"
    local RETVAL=0
    ((TOTAL=TOTAL+1))
    if [ "$TEST" == "includes" ]; then
      local RESULT=$(printf "$DATA" | grep -o "$WHAT")
      if [ -z "$RESULT" ]; then
        RETVAL=1
      fi
    fi
    if [ "$RETVAL" -eq 0 ]; then
      echo "Content found as expected ($WHAT)"
    else
      >&2 echo "Content not found ($WHAT)"
      dump_data "$DATA"
      ((FAILED=FAILED+1))
    fi
    return $RETVAL
}

function get_cookie_value() {
    local DATA="$1"
    local COOKIE=$(printf '%s' "$DATA" | grep -o -E 'Set\-Cookie\: .*?;Expires=.{27}')
    local VALUE=$(printf '%s' "${COOKIE:12}" | grep -o -E '^[^;]*?')
    printf '%s' "$VALUE"
}

function run_tests() {
  local STATIC1_RAW=$(execute_request "Static content should not get to the backend" GET "$URL/")
  print_header "$STATIC1_RAW"
  test_status "$STATIC1_RAW" 200

  local AUTH1=$(printf '%s' "$USER:$PASS" | base64)
  local LOGIN1_RAW=$(execute_request "Authentication correctly" GET "$URL/api/user/apikey/" "Basic $AUTH1")
  print_header "$LOGIN1_RAW"
  test_status "$LOGIN1_RAW" 200
  test_cookie "$LOGIN1_RAW" "exists";
  local LOGIN1_COOKIE=$(get_cookie_value "$LOGIN1_RAW")

  local AUTH2=$(printf '%s' "$USER:jotainihanmuuta" | base64)
  local LOGIN2_RAW=$(execute_request "Authentication with incorrect credentials" GET "$URL/api/user/apikey/" "Basic $AUTH2")
  print_header "$LOGIN2_RAW"
  test_status "$LOGIN2_RAW" 401
  test_cookie "$LOGIN2_RAW" "empty";

  local LOGIN3_RAW=$(execute_request "Authentication endpoint with OPTIONS" OPTIONS "$URL/api/user/apikey/")
  print_header "$LOGIN3_RAW"
  test_status "$LOGIN3_RAW" 200
  test_cookie "$LOGIN3_RAW" "missing";

  local APICALL1_RAW=$(execute_request "API call without cookie" GET "$URL/api/v0/should-not/be-in-backend-logs/")
  print_header "$APICALL1_RAW"
  test_status "$APICALL1_RAW" 401
  test_cookie "$APICALL1_RAW" "missing";

  local APICALL2_RAW=$(execute_request "API call with cookie" GET "$URL/api/v0/should/be-in-backend-logs/" "Bearer: $TOKEN" "$LOGIN1_COOKIE")
  print_header "$APICALL2_RAW"
  test_status "$APICALL2_RAW" 200
  test_cookie "$APICALL2_RAW" "exists";
  test_content "$APICALL2_RAW" "includes" '"url":"/api/v0/should/be-in-backend-logs/"'

  local TAMPERED_COOKIE=$(printf '%s' "$LOGIN1_COOKIE" | sed 's/1/2/g')
  local APICALL3_RAW=$(execute_request "API call with tampered cookie" GET "$URL/api/v0/should-not/be-in-backend-logs/" "Bearer: $TOKEN" "$TAMPERED_COOKIE")
  print_header "$APICALL3_RAW"
  test_status "$APICALL3_RAW" 401
  test_cookie "$APICALL3_RAW" "empty";

  local LOGOUT1_RAW=$(execute_request "Logout" GET "$URL/api-auth/logout/")
  print_header "$LOGOUT1_RAW"
  test_status "$LOGOUT1_RAW" 200
  test_cookie "$LOGOUT1_RAW" "empty";

  local BE_LOGS=$(docker logs $BE_INSTANCE)
  local SHOULD_NOTS=$(printf '%s' "$BE_LOGS" | grep '/should-not/' | wc -l)
  ((TOTAL=TOTAL+1))
  if [ "$SHOULD_NOTS" -gt 0 ]; then
    local LINE=$(printf '%s\n%s' "TITLE: Unauthorized requests in the backend" " ")
    print_header "$LINE"
    echo "There is $SHOULD_NOTS request lines on backend log that should not be there"
    ((FAILED=FAILED+1))
  fi
}

run_tests
((SUCCESS=TOTAL-FAILED))
echo ""
echo "RESULTS: Total: $TOTAL; Success: $SUCCESS; Failed: $FAILED"

EXITVAL=0
if [ "$FAILED" -gt 0 ]; then
  printf '\n%s\n%s\n%s\n\n' '##' '# FRONTEND SERVER LOGS' '##'
  docker logs $FE_INSTANCE
  printf '\n%s\n%s\n%s\n\n' '##' '# BACKEND SERVER LOGS' '##'
  docker logs $BE_INSTANCE
  EXITVAL=1
fi

docker stop $FE_INSTANCE || echo 'Unable to stop Frontend instance'
docker stop $BE_INSTANCE || echo 'Unable to stop Backend instance'
echo "Done!"
exit $EXITVAL
