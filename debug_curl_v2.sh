curl "https://html-ai-template.moestaging.com/api/v1/bff/response/stream?user_id=arijit.das@moengage.com&session_id=744d569d-d0e2-42b2-9f26-271fc666d0f5&agent_id=inapp-html-ai-v1" \
  -H "accept: application/json" \
  -H "accept-language: en-US,en;q=0.9" \
  -H "authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjE1NzI1MTI0NTciLCJ0eXAiOiJKV1QifQ.eyJhcHAiOnsiYXBwX2tleSI6IkNNNEQxTFpOMklNSk5CWTlVTFhBVTczRCIsImRiX25hbWUiOiJ6YWluX2luYXBwIiwiZGlzcGxheV9uYW1lIjoiemFpbl9pbmFwcCIsImVudmlyb25tZW50IjoibGl2ZSIsImlkIjoiNjM5ODUyZWViMGVjOWFiMzhhNzkyMTg5In0sImV4cCI6MTc3MTMwMjc0NiwiaWF0IjoxNzY2MDQ2NzQ2LCJpc3MiOiJhcHAubW9lbmdhZ2UuY29tIiwibmJmIjoxNzY2MDQ2NzQ2LCJyb2xlIjoiQWRtaW4iLCJ1c2VyIjp7IjJGQSI6dHJ1ZSwiZW1haWwiOiJhcmlqaXQuZGFzQG1vZW5nYWdlLmNvbSIsImlkIjoiNjNkY2VmODc4MGU5MzdiODljMTRjYjM3IiwibG9naW5fdHlwZSI6IlNURCJ9fQ.cCfP8y73ClnomYmWXyzr1CD3K74DebO5zHWwCMitzxxcdJ73HZTDepkz-5ufdRwnx10YchsrlqTx2aktESzi_zSq3VptSJr6s9WZVS8zs_43QcPSB5E0B6a6Ijo6qdwdnA9fyafdgs7LWw_XaJt9Fu4Mb2lQYjeV1wZb5kY8Vs76f7rIr81Bpaoa70-_Z3rfSteD3_N3gicJ4eKZVqmxYrX-GbIiGuN6kNthm-Wz9_cbbuIde4lhALrzje1y9AKIJZxCRYi5d8FBpnnAj4YWg6IB6mwG3rIvhgM7O-_Zm27IiDGAlEAxYAvYB7tsOVRZusm_a5SEqqJlChmuyidaPw" \
  -H "content-type: application/json" \
  -b "moe_c_s=1; moe_uuid=56baa3f7-285d-49c1-b67e-5482e2755748; moe_u_d=HcfBCoAgDADQf9m5XdSl9jOiboNACDJP0b8nHt8LPV2N4dDcumzAKTPL9HOPxXFOgK1UPZuIFIKgC5Ew-lzQOxYtVIzuFr4f; moe_s_n=RYpBDsMgDAT_4nOQMBgb8pWqshqcSlXV9kBuVf4eyCW33Zn5Q9M3zGAZqVgQt4SVHLH1tdTqRJ6JsZI9rMDU46YbzCjMkXzMgoyDfk6avZ-g6ku3cW_3YdarD1hCij356k9bp2k_AA" \
  -H "moetraceid: 6e7fac1e-080f-405c-8974-02f15bd956a9" \
  -H "origin: https://html-ai-template.moestaging.com" \
  -H "page: inapp/create/" \
  -H "priority: u=1, i" \
  -H "refreshtoken: 0d403795-1b35-4e7f-a919-becae42ef23f" \
  -H "sec-ch-ua: \"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"" \
  -H "sec-ch-ua-mobile: ?0" \
  -H "sec-ch-ua-platform: \"Windows\"" \
  -H "sec-fetch-dest: empty" \
  -H "sec-fetch-mode: cors" \
  -H "sec-fetch-site: same-origin" \
  -H "user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36" \
  --data-raw '{"payload":{"type":"user","text":"Create a spin the wheel template for marketer.Do not ask for clarification. If details are missing, make a reasonable assumption based on the context and proceed. If multiple valid options exist, choose the most common one. Your goal is to provide a final answer in the first response."}}' \
  > stream_debug.json
