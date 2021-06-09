local resty_sha1 = require "resty.sha1"
local resty_string = require "resty.string"

local function get_cookie_salt()
    return ngx.var.dynamicsalt
end

local function sha1str(str)
    local sha1 = resty_sha1:new()
    sha1:update(str)
    local digest = sha1:final()
    return resty_string.to_hex(digest)
end

local function create_security_hash(value)
    return sha1str(get_cookie_salt() .. value)
end

local function create_cookie_hash(timestamp, session_id)
    return sha1str(ngx.var.staticsalt .. timestamp .. get_cookie_salt() .. session_id)
end

local function create_session_id()
    return ngx.encode_base64(ngx.var.remote_addr, true) -- we could use binary_remote_addr
end

local function delete_cookie(name, params)
    if name == nil then
      return ""
    end
    local s = ''
    if (params['wildcard'] ~= nil) then
        s = s .. ';Domain=' .. ngx.var.front_host
    end
    if (params['httponly'] ~= nil) then
        s = s .. ';HttpOnly'
    end
    if (params['samesite'] ~= nil) then
        s = s .. ';SameSite=Lax'
    end
    if (params['secure'] ~= nil) then
        s = s .. ';Secure'
    end
    if (params['max_age'] ~= nil) then
        s = s .. ';Max-Age=' .. params['max_age']
    end
    local expires = ngx.time() - 86400
    return name .. "=" .. s ..";Path=/varda;Expires=" .. ngx.cookie_time(expires)
end

local function create_cookie_str(expired)
    local timestamp = ngx.time()
    local session_id = create_session_id()
    local expires = nil
    local cookiestr = nil
    if expired then
        expires = ngx.time() - 86400
        cookiestr = ""
    else
        expires = ngx.time() + ngx.var.sessionlifetime
        local hash = create_cookie_hash(timestamp, session_id)
        cookiestr = timestamp .. ":" .. session_id .. ":" .. hash
    end
    return ngx.var.sessionname .. "=" .. cookiestr .. ";path=/varda;"
            .. ngx.var.sessionsecure .. "HttpOnly;SameSite=Lax;Expires=" .. ngx.cookie_time(expires)
end

local function create_expired_cookie_str()
    return create_cookie_str(true)
end

local function validate_cookie_str(str)
    return validate_cookie_data(extract_cookie_str(str))
end

local function validate_cookie_data(data)
    local hash = create_cookie_hash(data['timestamp'], create_session_id())
    return (hash and data.hash and hash == data.hash)
end

local function extract_cookie_str(str)
    local parts = string.gmatch(str, "[^:]+")
    local var_timestamp = 0
    local var_session_id = ""
    local var_request_hash = ""
    local n = 0
    for i in parts do
      if n == 0 then
        var_timestamp = (i * 1)
      end
      if n == 1 then
        var_session_id = i
      end
      if n == 2 then
        var_request_hash = i
      end
      n = n + 1
    end
    return {
        id = var_session_id,
        timestamp = var_timestamp,
        hash = var_request_hash,
    }
end

local function require_internal_auth(headers)
    -- Require authentication in form of sha1(dynamicsalt+staticsalt)
    local autho = headers['Authorization']
    if autho == nil then
        ngx.log(ngx.ERR, 'Authorization not found')
        return false
    end
    local hash = create_security_hash(ngx.var.staticsalt)
    if autho == 'Token ' .. hash then
        ngx.log(ngx.INFO, 'Accepted TOKEN')
        return true
    elseif autho == 'Basic ' .. ngx.encode_base64('Token:' .. hash) then
        ngx.log(ngx.INFO, 'Accepted BASIC')
        return true
    end
    ngx.log(ngx.ERR, 'Authorization not accepted')
    return false
end

local function get_statistics(stub)
    local stats = string.gsub(stub, '.-requests.-([0-9 ]+).*', '%1')
    local res = {}
    res['active'] = ngx.var.connections_active
    res['reading'] = ngx.var.connections_reading
    res['writing'] = ngx.var.connections_writing
    res['waiting'] = ngx.var.connections_waiting
    local n = 0
    local accepted = 0
    local handled = 0
    local requests = 0
    for num in stats:gmatch('[^ ]+') do
      if (n == 0) then
        res['accepted'] = tonumber(num)
      end
      if (n == 1) then
        res['handled'] = tonumber(num)
      end
      if (n == 2) then
        res['requests'] = tonumber(num)
      end
      n = n + 1
    end
    return res
end

local function set_content_disposition_header()
  if (ngx.resp.get_headers()['Content-Type'] == 'application/json') then
    ngx.header['Content-Disposition'] = 'attachment; filename="api.json"'
  end
end

return {
    require_internal_auth = require_internal_auth,
    delete_cookie = delete_cookie,
    create_security_hash = create_security_hash,
    create_expired_cookie_str = create_expired_cookie_str,
    create_cookie_str = create_cookie_str,
    extract_cookie_str = extract_cookie_str,
    validate_cookie_data = validate_cookie_data,
    validate_cookie_str = validate_cookie_str,
    get_statistics = get_statistics,
    set_content_disposition_header = set_content_disposition_header
}
