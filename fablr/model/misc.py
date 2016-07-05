"""
    model.misc
    ~~~~~~~~~~~~~~~~

    Includes helper functions for model classes and other lesser used
    model classes.

    :copyright: (c) 2014 by Helmgast AB
"""
from collections import namedtuple
from datetime import timedelta, date, datetime

import wtforms as wtf
from flask_wtf import Form  # secure form
from slugify import slugify as ext_slugify

from wtforms.compat import iteritems
from wtforms.widgets import TextArea
from flask_babel import lazy_gettext as _
import logging
from flask import current_app
from flask_mongoengine import Document  # Enhanced document
from mongoengine import (EmbeddedDocument, StringField, ReferenceField)

logger = current_app.logger if current_app else logging.getLogger(__name__)

METHODS = frozenset(['POST', 'PUT', 'PATCH', 'DELETE'])


def slugify(title):
    slug = ext_slugify(title)
    if slug.upper() in METHODS:
        return "%s_" % slug
    else:
        return slug


class Choices(dict):
    # def __init__(self, *args, **kwargs):
    #     if args:
    #         return dict.__init__(self, [(slugify(k), _(k)) for k in args])
    #     elif kwargs:
    #         return dict.__init__(self, {k:_(k) for k in kwargs})

    def __getattr__(self, name):
        if name in self.keys():
            return name
        raise AttributeError(name)

    def to_tuples(self, empty_value=False):
        tuples = [(s, self[s]) for s in self.keys()]
        if empty_value:
            tuples.append(('', ''))
        return tuples


def list_to_choices(list):
    return [(s.lower(), _(s)) for s in list]


def now():
    return datetime.now;


def translate_action(action, item):
    if action == 'patch':
        return _('"%(item)s" edited', item=item)
    elif action == 'post':
        return _('"%(item)s" created', item=item)
    elif action == 'put':
        return _('"%(item)s" replaced', item=item)
    elif action == 'delete':
        return _('"%(item)s" deleted', item=item)
    else:
        return ''


FilterOption = namedtuple('FilterOption', 'kwargs label')


def numerical_options(field_name, spans=None, labels=None):
    rv = []
    if not spans:
        raise ValueError("Need at least one value to span options for")
    own_labels = isinstance(labels, list)
    if own_labels and len(labels) != len(spans) + 1:
        raise ValueError("Need one label more than items in spans, as the last label 'More than [last value of spans]'")
    for idx, span in enumerate(spans):
        if own_labels:
            rv.append(FilterOption(kwargs={field_name + '__lte': span, field_name + '__gt': None}, label=labels[idx]))
        else:
            rv.append(FilterOption(kwargs={field_name + '__lte': span, field_name + '__gt': None},
                                   label=_('Less than %(val)s', val=span)))
    # Add last filter value, as more than the highest value of span
    if own_labels:
        rv.append(FilterOption(kwargs={field_name + '__gt': spans[-1], field_name + '__lte': None}, label=labels[-1]))
    else:
        rv.append(FilterOption(kwargs={field_name + '__gt': spans[-1], field_name + '__lte': None},
                               label=_('More than %(val)s', val=spans[-1])))

    def return_function(*args):
        return rv

    return return_function


def reference_options(field_name, model):
    def return_function(*args):
        return [FilterOption(kwargs={field_name: o.slug}, label=o.title) for o in model.objects().distinct(field_name)]

    return return_function


def choice_options(field_name, choices):
    rv = [FilterOption(kwargs={field_name: a}, label=b) for a, b in choices]

    def return_function(*args):
        return rv

    return return_function


def datetime_options(field_name, time_deltas=None):
    rv = []
    # 'Last %(d)s days, %(h)s hours, %(m)s minutes, %(s)s seconds'
    if not time_deltas:
        raise ValueError("Need at least one value in time_deltas")

    # We pre-compute the filter choices in a intermediary form, without the dicts
    # Will be completed in the return_function below
    for t in time_deltas:
        if isinstance(t, tuple):
            rv.append((field_name + '__gte', field_name + '__lt', t[0], t[1]))
        else:
            rv.append((field_name + '__gte', field_name + '__lt', t, _('Last %(val)s days', val=t.days)))
    rv.append((field_name + '__lt', field_name + '__gte', time_deltas[-1],
               _('Older than %(val)s days', val=time_deltas[-1].days)))

    def return_function(*args):
        # Rebuild above list of tuples to one with dict, and make time - timedelta
        return [FilterOption(kwargs={x[0]: date.today() - x[2], x[1]: None}, label=x[3]) for x in rv]

    return return_function


from7to365 = [timedelta(days=7), timedelta(days=30), timedelta(days=90), timedelta(days=365)]


def distinct_options(field_name, model):
    def return_function(*args):
        values = model.objects().distinct(field_name)
        rv = [FilterOption(kwargs={field_name: v}, label=v) for v in values]
        return rv

    return return_function


Languages = Choices(
    en=_('English'),
    sv=_('Swedish')
)

Countries = Choices(
    AF="Afghanistan",
    AL="Albania",
    DZ="Algeria",
    AS="American Samoa",
    AD="Andorra",
    AO="Angola",
    AI="Anguilla",
    AQ="Antarctica",
    AG="Antigua and Barbuda",
    AR="Argentina",
    AM="Armenia",
    AW="Aruba",
    AU="Australia",
    AT="Austria",
    AZ="Azerbaijan",
    BS="Bahamas",
    BH="Bahrain",
    BD="Bangladesh",
    BB="Barbados",
    BY="Belarus",
    BE="Belgium",
    BZ="Belize",
    BJ="Benin",
    BM="Bermuda",
    BT="Bhutan",
    BO="Bolivia",
    BA="Bosnia and Herzegowina",
    BW="Botswana",
    BV="Bouvet Island",
    BR="Brazil",
    IO="British Indian Ocean Territory",
    BN="Brunei Darussalam",
    BG="Bulgaria",
    BF="Burkina Faso",
    BI="Burundi",
    KH="Cambodia",
    CM="Cameroon",
    CA="Canada",
    CV="Cape Verde",
    KY="Cayman Islands",
    CF="Central African Republic",
    TD="Chad",
    CL="Chile",
    CN="China",
    CX="Christmas Island",
    CC="Cocos (Keeling) Islands",
    CO="Colombia",
    KM="Comoros",
    CG="Congo",
    CD="Congo, the Democratic Republic of the",
    CK="Cook Islands",
    CR="Costa Rica",
    CI="Cote d'Ivoire",
    HR="Croatia (Hrvatska)",
    CU="Cuba",
    CY="Cyprus",
    CZ="Czech Republic",
    DK="Denmark",
    DJ="Djibouti",
    DM="Dominica",
    DO="Dominican Republic",
    TP="East Timor",
    EC="Ecuador",
    EG="Egypt",
    SV="El Salvador",
    GQ="Equatorial Guinea",
    ER="Eritrea",
    EE="Estonia",
    ET="Ethiopia",
    FK="Falkland Islands (Malvinas)",
    FO="Faroe Islands",
    FJ="Fiji",
    FI="Finland",
    FR="France",
    FX="France, Metropolitan",
    GF="French Guiana",
    PF="French Polynesia",
    TF="French Southern Territories",
    GA="Gabon",
    GM="Gambia",
    GE="Georgia",
    DE="Germany",
    GH="Ghana",
    GI="Gibraltar",
    GR="Greece",
    GL="Greenland",
    GD="Grenada",
    GP="Guadeloupe",
    GU="Guam",
    GT="Guatemala",
    GN="Guinea",
    GW="Guinea-Bissau",
    GY="Guyana",
    HT="Haiti",
    HM="Heard and Mc Donald Islands",
    VA="Holy See (Vatican City State)",
    HN="Honduras",
    HK="Hong Kong",
    HU="Hungary",
    IS="Iceland",
    IN="India",
    ID="Indonesia",
    IR="Iran (Islamic Republic of)",
    IQ="Iraq",
    IE="Ireland",
    IL="Israel",
    IT="Italy",
    JM="Jamaica",
    JP="Japan",
    JO="Jordan",
    KZ="Kazakhstan",
    KE="Kenya",
    KI="Kiribati",
    KP="Korea, Democratic People's Republic of",
    KR="Korea, Republic of",
    KW="Kuwait",
    KG="Kyrgyzstan",
    LA="Lao People's Democratic Republic",
    LV="Latvia",
    LB="Lebanon",
    LS="Lesotho",
    LR="Liberia",
    LY="Libyan Arab Jamahiriya",
    LI="Liechtenstein",
    LT="Lithuania",
    LU="Luxembourg",
    MO="Macau",
    MK="Macedonia, The Former Yugoslav Republic of",
    MG="Madagascar",
    MW="Malawi",
    MY="Malaysia",
    MV="Maldives",
    ML="Mali",
    MT="Malta",
    MH="Marshall Islands",
    MQ="Martinique",
    MR="Mauritania",
    MU="Mauritius",
    YT="Mayotte",
    MX="Mexico",
    FM="Micronesia, Federated States of",
    MD="Moldova, Republic of",
    MC="Monaco",
    MN="Mongolia",
    MS="Montserrat",
    MA="Morocco",
    MZ="Mozambique",
    MM="Myanmar",
    NA="Namibia",
    NR="Nauru",
    NP="Nepal",
    NL="Netherlands",
    AN="Netherlands Antilles",
    NC="New Caledonia",
    NZ="New Zealand",
    NI="Nicaragua",
    NE="Niger",
    NG="Nigeria",
    NU="Niue",
    NF="Norfolk Island",
    MP="Northern Mariana Islands",
    NO="Norway",
    OM="Oman",
    PK="Pakistan",
    PW="Palau",
    PA="Panama",
    PG="Papua New Guinea",
    PY="Paraguay",
    PE="Peru",
    PH="Philippines",
    PN="Pitcairn",
    PL="Poland",
    PT="Portugal",
    PR="Puerto Rico",
    QA="Qatar",
    RE="Reunion",
    RO="Romania",
    RU="Russian Federation",
    RW="Rwanda",
    KN="Saint Kitts and Nevis",
    LC="Saint LUCIA",
    VC="Saint Vincent and the Grenadines",
    WS="Samoa",
    SM="San Marino",
    ST="Sao Tome and Principe",
    SA="Saudi Arabia",
    SN="Senegal",
    SC="Seychelles",
    SL="Sierra Leone",
    SG="Singapore",
    SK="Slovakia (Slovak Republic)",
    SI="Slovenia",
    SB="Solomon Islands",
    SO="Somalia",
    ZA="South Africa",
    GS="South Georgia and the South Sandwich Islands",
    ES="Spain",
    LK="Sri Lanka",
    SH="St. Helena",
    PM="St. Pierre and Miquelon",
    SD="Sudan",
    SR="Suriname",
    SJ="Svalbard and Jan Mayen Islands",
    SZ="Swaziland",
    SE="Sweden",
    CH="Switzerland",
    SY="Syrian Arab Republic",
    TW="Taiwan, Province of China",
    TJ="Tajikistan",
    TZ="Tanzania, United Republic of",
    TH="Thailand",
    TG="Togo",
    TK="Tokelau",
    TO="Tonga",
    TT="Trinidad and Tobago",
    TN="Tunisia",
    TR="Turkey",
    TM="Turkmenistan",
    TC="Turks and Caicos Islands",
    TV="Tuvalu",
    UG="Uganda",
    UA="Ukraine",
    AE="United Arab Emirates",
    GB="United Kingdom",
    US="United States",
    UM="United States Minor Outlying Islands",
    UY="Uruguay",
    UZ="Uzbekistan",
    VU="Vanuatu",
    VE="Venezuela",
    VN="Viet Nam",
    VG="Virgin Islands (British)",
    VI="Virgin Islands (U.S.)",
    WF="Wallis and Futuna Islands",
    EH="Western Sahara",
    YE="Yemen",
    YU="Yugoslavia",
    ZM="Zambia",
    ZW="Zimbabwe",
)


class Address(EmbeddedDocument):
    name = StringField(max_length=60, required=True, verbose_name=_('Name'))
    street = StringField(max_length=60, required=True, verbose_name=_('Street'))
    zipcode = StringField(max_length=8, required=True, verbose_name=_('ZIP Code'))
    city = StringField(max_length=60, required=True, verbose_name=_('City'))
    # Tuples come unsorted, let's sort first
    country = StringField(choices=sorted(Countries.to_tuples(), key=lambda tup: tup[1]), required=True,
                          default=Countries.SE,
                          verbose_name=_('Country'))
    mobile = StringField(max_length=14, verbose_name=_('Cellphone Number'))


class GeneratorInputList(Document):
    name = StringField()

    def items(self):
        return GeneratorInputItem.select().where(GeneratorInputItem.input_list == self)


class GeneratorInputItem(Document):
    input_list = ReferenceField(GeneratorInputList)
    content = StringField()


class StringGenerator(Document):
    name = StringField()
    description = StringField()
    generator = None

    def __unicode__(self):
        return self.name
