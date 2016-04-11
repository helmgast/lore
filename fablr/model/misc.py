"""
    model.misc
    ~~~~~~~~~~~~~~~~

    Includes helper functions for model classes and other lesser used
    model classes.

    :copyright: (c) 2014 by Helmgast AB
"""

import datetime

import wtforms as wtf
from flask.ext.wtf import Form  # secure form
from slugify import slugify as ext_slugify

# import RadioField, BooleanField, SelectMultipleField, StringField, wtf.validators, widgets
from wtforms.compat import iteritems
from wtforms.widgets import TextArea
from flask.ext.babel import lazy_gettext as _
from fablr.app import STATE_TYPES, FEATURE_TYPES
import logging
from collections import OrderedDict
from flask import current_app
from flask.ext.mongoengine import Document  # Enhanced document
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
    return datetime.datetime.now;


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
    name = StringField(max_length=60, verbose_name=_('Name'))
    street = StringField(max_length=60, verbose_name=_('Street'))
    zipcode = StringField(max_length=8, verbose_name=_('ZIP Code'))
    city = StringField(max_length=60, verbose_name=_('City'))
    # Tuples come unsorted, let's sort first
    country = StringField(choices=sorted(Countries.to_tuples(), key=lambda tup: tup[1]), default=Countries.SE, verbose_name=_('Country'))
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


class ApplicationConfigForm(Form):
    backup = wtf.BooleanField(_('Do backup'))
    backup_name = wtf.StringField(_('Backup name'), [wtf.validators.Length(min=6)])
    state = wtf.RadioField(_('Application state'), choices=STATE_TYPES)
    features = wtf.SelectMultipleField(_('Application features'), choices=FEATURE_TYPES,
                                       option_widget=wtf.widgets.CheckboxInput(),
                                       widget=wtf.widgets.ListWidget(prefix_label=False))


class MailForm(Form):
    to_field = wtf.StringField(_('To'), [wtf.validators.Email(), wtf.validators.Required()])
    from_field = wtf.StringField(_('From'), [wtf.validators.Email(), wtf.validators.Required()])
    subject = wtf.StringField(_('Subject'), [wtf.validators.Length(min=1, max=200), wtf.validators.Required()])
    message = wtf.StringField(_('Message'), widget=TextArea())

    def process(self, formdata=None, obj=None, allowed_fields=None, **kwargs):
        # Formdata overrides obj, which overrides kwargs.
        # We need to filter formdata to only touch allowed fields.
        # Finally, we need to only use formdata for the fields it is defined for, rather
        # than default behaviour to reset all fields with formdata, regardless if empty
        for name, field, in iteritems(self._fields):
            # Use formdata either if no allowed_fields provided (all allowed) or
            # if field exist in allowed_fields
            if allowed_fields == None or name in allowed_fields:
                field_formdata = formdata
                print "Field %s will get formdata" % name
            else:
                field_formdata = None
                field.flags.disabled = True
                print "Field %s is disabled from getting formdata" % name

            if obj is not None and hasattr(obj, name):
                field.process(field_formdata, getattr(obj, name))
            elif name in kwargs:
                field.process(field_formdata, kwargs[name])
            else:
                field.process(field_formdata)
