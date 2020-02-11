Localization
==================================================================
There are two types of internationalization - interface and content.
Interface can be automatically changed but content depends on if it's 
available in that content item. Currently, no content items support multiple
languages. There is never any reason to intentionally have different interface
and content language, but may happen if content of specific language is not available.

Language input can be in reverse order of importance:

* In HTTP header (can be multiple)
* In visitor preference (cookie or user profile)
* In URL

URL is special - it should give a 404 if the requested language is not available 
as interface (ignoring content). Otherwise, we shall build a list of languages
in order of preference, with user preference ordered first. This should be matched
with the set of languages supported by interface and content respectively.

E.g.: Header says EN, SE. User says DE. Check in order DE, EN, SE vs available
interface language (EN, SE) and content (SE).

Language output is in form of:

* Displayed interface language
* Displayed content language
* Language code in HTML header
* Preselected language and locale details in relevant forms
* Dates and times-formatting (locale)
* HTML lang field
* Error messages

In addition, location means which country the visitor is likely from.