import pytest
import json
import responses
from lore.model.asset import sniff_remote_file, FileAsset


# def test_make_slug():

#     slug = FileAsset.make_slug('Järn Världsträdets grenar 20200423.pdf', 'application/pdf')
#     assert slug == 'jarn_ar_grejer.pdf'

# def test_sniff():
#     metadata = sniff_remote_file('https://drive.google.com/uc?export=view&id=1Cdg4wk-RTz8zd3POHGkWiJtUjrXMlUIA')
#     assert metadata['fname'] == 'Järn Världsträdets grenar 20200423.pdf'


# GET https://drive.google.com/uc?export=download&id=1zrZTkPr5BxLSrNdg9dwvOLoVDLkR_tOO

# X-GUploader-UploadID: AAANsUlNJhv6bjJMmym4V1CAzdsWB-3RgGnICFGTreyc5pJuNvrQcpP6OhZeo0NhE-mM3Y1bPeyfxm7OkqhVLHGsZAKzfYNvVQ
# Access-Control-Allow-Origin: *
# Access-Control-Allow-Credentials: false
# Access-Control-Allow-Headers: Accept, Accept-Language, Authorization, Cache-Control, Content-Disposition, Content-Encoding, Content-Language, Content-Length, Content-MD5, Content-Range, Content-Type, Date, GData-Version, google-cloud-resource-prefix, Host, If-Match, If-Modified-Since, If-None-Match, If-Unmodified-Since, Origin, OriginToken, Pragma, Range, Slug, Transfer-Encoding, Want-Digest, x-chrome-connected, X-ClientDetails, X-Client-Version, X-Firebase-Locale, X-Goog-Firebase-Installations-Auth, X-Firebase-Client, X-Firebase-Client-Log-Type, X-GData-Client, X-GData-Key, X-GoogApps-Allowed-Domains, X-Goog-AdX-Buyer-Impersonation, X-Goog-Api-Client, X-Goog-AuthUser, x-goog-ext-124712974-jspb, x-goog-ext-259736195-jspb, X-Goog-PageId, X-Goog-Encode-Response-If-Executable, X-Goog-Correlation-Id, X-Goog-Request-Info, X-Goog-Request-Reason, X-Goog-Experiments, x-goog-iam-authority-selector, x-goog-iam-authorization-token, X-Goog-Spatula, X-Goog-Travel-Bgr, X-Goog-Travel-Settings, X-Goog-Upload-Command, X-Goog-Upload-Content-Disposition, X-Goog-Upload-Content-Length, X-Goog-Upload-Content-Type, X-Goog-Upload-File-Name, X-Goog-Upload-Header-Content-Length, X-Goog-Upload-Offset, X-Goog-Upload-Protocol, x-goog-user-project, X-Goog-Visitor-Id, X-Goog-FieldMask, X-Google-Project-Override, X-Goog-Api-Key, X-HTTP-Method-Override, X-JavaScript-User-Agent, X-Pan-Versionid, X-Proxied-User-IP, X-Origin, X-Referer, X-Requested-With, X-Stadia-Client-Context, X-Upload-Content-Length, X-Upload-Content-Type, X-Use-HTTP-Status-Code-Override, X-Ios-Bundle-Identifier, X-Android-Package, X-Ariane-Xsrf-Token, X-YouTube-VVT, X-YouTube-Page-CL, X-YouTube-Page-Timestamp, X-Goog-Meeting-Botguardid, X-Goog-Meeting-Debugid, X-Goog-Meeting-Token, X-Client-Data, X-Sfdc-Authorization, MIME-Version, Content-Transfer-Encoding, X-Earth-Engine-App-ID-Token, X-Earth-Engine-Computation-Profile, X-Earth-Engine-Computation-Profiling, X-Play-Console-Experiments-Override, X-Play-Console-Session-Id, x-alkali-account-key, x-alkali-application-key, x-alkali-auth-apps-namespace, x-alkali-auth-entities-namespace, x-alkali-auth-entity, x-alkali-client-locale, EES-S7E-JSON
# Access-Control-Allow-Methods: GET,OPTIONS
# P3P: CP="This is not a P3P policy! See http://www.google.com/support/accounts/answer/151657?hl=en for more info."
# Content-Range: bytes 0-1/767041
# Content-Type: image/png
# Content-Disposition: attachment;filename="anon_2d-1200px.png";filename*=UTF-8''anon_2d-1200px.png
# Date: Sat, 25 Apr 2020 09:32:01 GMT
# Expires: Sat, 25 Apr 2020 09:32:01 GMT
# Cache-Control: private, max-age=0
# Content-Length: 2
# Server: UploadServer

# GET https://shopcdn.textalk.se/shop/ws51/49251/art51/h1595/171461595-origpic-6600e7.png

# Content-Type: image/png
# Transfer-Encoding: chunked
# Connection: keep-alive
# Server: nginx
# Date: Sat, 25 Apr 2020 20:15:29 GMT
# Expires: Fri, 02 Apr 2021 13:23:48 GMT
# Cache-Control: public, max-age=31536000, immutable
# ETag: "Te9a3a2aecee69c82adbbdacee9550a37"
# Last-Modified: Sun, 27 Oct 2019 15:55:06 GMT
# X-Cache-Status: HIT
# X-Cache: Miss from cloudfront
# Via: 1.1 6a4ac6dc45d50207c441c9986e5019a0.cloudfront.net (CloudFront)
# X-Amz-Cf-Pop: ARN53
# X-Amz-Cf-Id: sYxWrgGuxxqamcqXL2ln5Q-UoR1gbnt6pofT-PC95goLceF5M9zeBg==

# GET https://drive.google.com/open?id=1zrZTkPr5BxLSrNdg9dwvOLoVDLkR_tOO

# Content-Type: text/html; charset=utf-8
# X-Robots-Tag: noindex, nofollow, nosnippet
# Cache-Control: no-cache, no-store, max-age=0, must-revalidate
# Pragma: no-cache
# Expires: Mon, 01 Jan 1990 00:00:00 GMT
# Date: Sat, 25 Apr 2020 20:16:23 GMT
# Transfer-Encoding: chunked
# X-Content-Type-Options: nosniff
# X-Frame-Options: SAMEORIGIN
# Content-Security-Policy: frame-ancestors 'self'
# X-XSS-Protection: 1; mode=block
# Server: GSE

# def test_sniff(mocked_responses):
#     mocked_responses.add(
#         responses.GET, 'https://server.com/testfile.png',
#         body='{}', status=200,
#         content_type='image/png')
