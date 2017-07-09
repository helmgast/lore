import re
from hashlib import md5

"""
PDF fingerprint

We need to insert a User ID in a few places into the document.
We will take the UID, make it MD5, and take the first 12 characters (HEX).
Those have very low probability of collision, even if it's just a subset of
the full MD5. We want the HEX uppercase. As we have MD5 it, it's impossible to
get the user ID back, and it also protects us from user id of different lengths
throughout the versions of the watermark. The UID could be email as well, for example.

Adobe Document ID in file trailer
<</Size 5226/Root 5168 0 R/Info 340 0 R/ID[<DE237A7714166B438254F2E7CAEACB2B><0A856D2F0DE97146B3FC7DBBA75F5CEB>]/Prev 1348532/XRefStm 2964>>
Not specified how long but seems to be a 16byte/32hex uppercase string, first is original ID and second is instance id.
Regex: trailer\s+<<.*?ID\[<(.{12})
Replace matching group with user ID

XMP Metadata DocumentID
<xmpMM:DocumentID>xmp.did:E9E3ECA55654E311B947ECCF20247A3D</xmpMM:DocumentID>
This is the document ID, created every time making a "Save As" (but not when making Save).
Regex: <xmpMM:DocumentID>xmp.did:(.{12})
Replace matching group with user ID

/FontFamily
FontDescriptors in the document will include a /FontFamily value. This is used if fonts
are not embedded, to find other suitable fonts. This is not easy to find from outside.
<</Ascent 868/CapHeight 670/Descent -266/Flags 98/FontBBox[-170 -266 1013 868]/FontFamily(Goudy Old Style)/FontFile2 5199 0 R/FontName/FLTYGY+GoudyOldStyleT-Italic/FontStretch/Normal/FontWeight 400/ItalicAngle -8/StemV 56/Type/FontDescriptor/XHeight 397>>
Regex: /FontFamily\(([^)]{12})
Above should only match and replace once.

When we check a document for fingerprint, we first extract all matching patterns from above.
The only change is that for the matching groups, we instead look for uppercase hex only, [0-9A-F]
If find multiple matches, compare them and throw an error if they don't match.
Then, download all user IDs, MD5 each and then search through by comparing each match we had.
If a user matches just one, we basically know that they are the ones that downloaded the document.
"""


def hex(s):
    return ' '.join(x.encode('hex') for x in s)


pdf_id = re.compile(r'trailer\s+<<.*?ID\[<(.{12})')  # may be multiline
doc_id = re.compile(r'<xmpMM:DocumentID>xmp.did:(.{12})')  # wouldn't be multiline
font_id = re.compile(r'/FontFamily\(([^)]{12})')  # wouldn't be multiline
font_id_find = re.compile(r'/FontFamily\(([0-9A-F]{12})')  # Only look for hex characters

window_size = 512  # size in bytes of the sliding window


def fingerprint_from_user(user_id):
    return md5(str(user_id)).hexdigest()[:12].upper()  # first 12 chars of hexdigest


def fingerprint_pdf(file_object, user_id):
    """Generator that will fingerprint a PDF"""
    uid = fingerprint_from_user(user_id)
    print "Fingerprinting uid %s as hash %s" % (user_id, uid)
    pdf_id_num, doc_id_num, font_id_num = 0, 0, 0
    window = file_object.read(window_size * 2)
    buf = window  # just to start with a buffer that equals true
    do_yield = True
    while buf:
        if not pdf_id_num:
            m = pdf_id.search(window)
            if m:
                window = window[:m.start(1)] + uid + window[m.start(1) + 12:]
                pdf_id_num += 1
            # print window[m.start(0) : window.find('\n', m.start(1))]
        if not doc_id_num:
            m = doc_id.search(window)
            if m:
                window = window[:m.start(1)] + uid + window[m.start(1) + 12:]
                doc_id_num += 1
            # print window[m.start(0) : window.find('\n', m.start(1))]
        if not font_id_num:
            m = font_id.search(window)
            if m:
                window = window[:m.start(1)] + uid + window[m.start(1) + 12:]
                font_id_num += 1
            # print window[m.start(0) : window.find('\n', m.start(1))]

        # We use a sliding window which means we can't yield every loop,
        # it would duplicate half window in the output
        if do_yield:
            yield window
        do_yield = not do_yield
        buf = file_object.read(window_size)
        window = window[window_size:] + buf


def get_fingerprints(file):
    fingerprints = []
    with open(file, 'rb') as f:
        window = f.read(window_size * 2)
        buf = window  # just to start with a buffer that equals true
        while buf:
            # Todo - if we find something, it's often found twice as the window
            # overlaps, so fix this
            m = pdf_id.search(window)
            if m:
                print "Found %s in %s" % (m.group(1), window[m.start(0): window.find('\n', m.start(1))])
                fingerprints.append(m.group(1))
            m = doc_id.search(window)
            if m:
                print "Found %s in %s" % (m.group(1), window[m.start(0): window.find('\n', m.start(1))])
                fingerprints.append(m.group(1))
            m = font_id_find.search(window)
            if m:
                print "Found %s in %s" % (m.group(1), window[m.start(0): window.find('\n', m.start(1))])
                fingerprints.append(m.group(1))
            buf = f.read(window_size)
            window = window[window_size:] + buf
    return fingerprints

# obj = re.compile(r'\d+ \d+ obj\s+<<(.+?)>>(stream(.*?)endstream)?\s+endobj', re.DOTALL)
# linearized = re.compile(r'<<\s*/Linearized.+?>>', re.DOTALL)
# lin_firstpage = re.compile(r'/O\s*(\d+)')
# lin_length = re.compile(r'/L\s*(\d+)')
# lin_firstpage_offset = re.compile(r'/E\s*(\d+)')
# lin_reftable_offset = re.compile(r'/T\s*(\d+)')
# lin_hint_offset = re.compile(r'/H\s*\[\s*(\d+)')
# lin_hint_length = re.compile(r'/H\s*\[\s*\d+\s*(\d+)\s*\]')
# xref_size = re.compile(r'<<\s*/Size.+?>>', re.DOTALL)
# xref_prev = re.compile(r'/Prev\s*(\d+)')
# xref_stm = re.compile(r'/XRefStm\s*(\d+)')

# xref_head = re.compile(r'xref\s+(\d+)\s+(\d+)')
# xref_line = re.compile(r'(\d{10})\s+(\d{5})\s+(\w{1})')


# Bytemark = namedtuple('Bytemark', ['value', 'offset', 'length'])

# def mark_from_match(match, offset=0):
# 	print match.group(0)
# 	bm = Bytemark(match.group(1), match.start(1)+offset, len(match.group(1)))
# 	print bm
# 	return bm

# bytemarks = OrderedDict()

# print "Xref at %i" %contents.rfind("xref")
# startxref = contents.rfind("xref")
# xref_table = contents[contents.rfind("xref", 0, startxref):]
# xref_head.finditer(xref_table)
# for match in pattern.finditer(contents):
# 	if match.lastindex >= 1:
# 		filter_head = match.group(1)
# 		if filter_head.startswith("/Filter/FlateDecode"):
# 			stream = match.group(3).strip('\r\n') # need to be explicit what to strip or it may take too much
# 			print "Found stream of length %i, (%s)" % (len(stream), filter_head)
# 			print hex(stream)
# 			decomp = zlib.decompress(stream)
# 			print "Decompressed"
# 			print hex(decomp)
# 			#decomp = decomp.replace("Binder", "Fisting")
# 			# comp = zlib.compress(decomp, 9)
# 			compobj = zlib.compressobj(9, zlib.DEFLATED, 12)
# 			comp = compobj.compress(decomp)
# 			comp += compobj.flush(zlib.Z_FINISH)
# 			print "New stream length is %i" % len(comp)
# 			print hex(comp)
# 			print "Decompressed again"
# 			print hex(zlib.decompress(comp))
# 			print "Compress again"
# 			print hex(zlib.compress(comp, 9))
# 			raw_input()


# PDF format

# PDFs are updated by prepending a new XREF table above the document, and readers
# are supposed to read from bottom and up.
# If saved with "Fast Web View", the PDF starts with first page:
# http://labs.appligent.com/pdfblog/linearization/

# /Linearized 1 #
# /O 193 # object number of first page
# /H [ 1203 800 ] # location of hint stream
# /L 621019 # length of file in bytes, should be updated
# /E 260336 # byte offset to end of first page
# /N 15 # number of pages in doc
# /T 617080 # the offset of the white-space character preceding the first entry
# 			of the main cross-reference table (the entry for object number 0)
# 			should be updated
# After the linearized comes a trailer with a Prev value. That points to the
# main xref table in byte offset and should also be updated.

# xref
# <objno> <no of objs>
# <10 byte offset> <generation/version no> n
# <...>

# File trailer, ends each part of file updated
# trailer
# << key1 value1
# key2 value2
# ...
# keyn valuen
# >>
# startxref
# Byte_offset_of_last_cross-reference_section
# %%EOF

# Three methods of water marking
# 1) Add/replace a line of text throughout the document (visible)
# 2) Hide metadata inside document objects
# 3) Append a new object with metadata
