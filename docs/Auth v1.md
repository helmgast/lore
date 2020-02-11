# Auth

New join/login flow:
First ask "who are you? (email)". When email is typed, if joining, optionally find public info tied to the email (gravatar?). Then ask "Prove it's you" (you can prove with either google, fb, password or simply getting a verification email that gives temporary access). It's possible for a user to have multiple authentication methods.
An email has status of "verified" or not. If not verified, user has to click a link in an email, or the social login has same email, which also verifies the email.
Optionally, when logging in, typing the email can also show who you are and which methods of logging in was used.
This method makes it more fluid to go between having just an email address, and having a fully registered, authenticated user.

# Lore auth

Lore and each publisher is likely to have multiple "properties", e.g domains needing sign in. Also, we will need to stitch together multiple tools with different use email management. So we need a centralized authentication source. Therefore we have chosen Auth0. Additionally it means a higher level of security and that failures in one of our tools won't affect the ability to authenticate.

Auth0 provides different connections, authentication sources. Although they can manage a database of users and passwords, we have chosen to only use Google, Facebook and one-time code to email. Auth0 also provided the actual login page from their servers. This means we don't need to manage passwords and the complication around them, and that users are more secure. 

A result of the multiple connections is that one individual might sign in with different IDs or emails, either knowingly or unknowingly. Additionally, many users have data attached to different emails over time, such as from Kickstarter. Together this means we need to link multiple emails to one individual. And once we have done that, we need to use this list of IDs to link to multiple accounts in our tools, eg forum, web, shop.

To solve this, we use Auth0 rules, that run as Node.JS functions in Auth0 servers, at the time a user signs in. These rules will take care of auto-linking accounts with same email, and can also initiate a merge of different emails, as well as sending email notice to users.

On each app, we need to go through a Oauth2 flow with Auth0 to authenticate a user. The authenticated email we received, we then use to activate a session in that app with an account with that email. If we need to, we can search through all linked email to find the first match in the apps user database.

Auth0 provides Single Sign On (SSO). It means we authenticate on one app we will auto-login on the next one. We however need to redirect the user to Auth0 so that it can automatically redirect back and set a session in the app, but the user won't notice much. But it means that as a user goes from web to forum, they don't need to sign in again.

To develop the authorization flow, we need to manage a small amount of code on rules deployed to Auth0 servers. We also need to manage a callback in each server based app that can receive the Oauth2 flow, locate the right app account and start a local session. Finally, existing apps need to be a bit modified add they usually have code and UI referring to their own authentication. It word be confusing for them to be able to login with a password on the app in a different way than with Auth0.


Basic assumptions:
- We use Auth0 as Auth-provider across the board, which gives us SSO over domains and apps
- Many users have multiple emails, and change over time

The main authentication problem we have, is that a person logins with email1 but have registered with email2. This is quite likely to happen. People use different emails for different social accounts, and may think that the email they should use is the one for Kickstarter, Textalk, or something similar.

We therefore need a way to tie emails together. We could do it in two ways:
- A primary email, and a set of secondary emails.
    - Pro: Email as main identifier is “human readable” in the database.
    - Pro: If the email is used as main ID, it will work with (any?) existing data store, whereas an ID-string may not have an obvious field in to store it and search it.
    - Con: The identified may have to change if an email is lost, which creates tricky life-cycle problems (e.g email needs to be changed across multiple user databases).
- Or, an account-number, and any number of emails attached to it.
    - Pro: an ID number on it’s own is not private data. (However, we still need to store emails?)
    - Pro: Never (?) needs to change.
    - Con: Need an extra field in a database, as we still need to store all emails.
    - Con: Need to be generated in some way that is guaranteed to be unique towards previous ones.
    - Con: If ID is the common theme, different apps might communicate to different emails, so that perhaps all webshop emails goes to a dead email whereas others goes to a live one. That can be complicated to deal with.

The assumption is therefore that we use a “primary email” as shared identifier. For the issue of changing primary email, we either need to build some own logic or assume it’s seldom enough that we can do it manually. (Adding more emails can be supported).

The login scenario is as follows: we can get an authenticated request from Auth0, with a user that has one or more methods to authenticate (e.g. Google, FB, email), to one of several applications with separate user stores (e.g. a wiki, webshop, forum or Lore domains). In the best of worlds, all of these applications would share the same user data store, but that is unrealistic as it’s often very tightly integrated. Instead, we need to keep the user stores light on data and with one common ID stored in some field.

1. If the request comes with a “Lore-email”, we know this user has used a Lore application before. But we cannot be sure if this “Lore-email” is also in this particular application (the user may have logged in to webshop once but never to forum). 
    1. If we can find a user with this “Lore-email”, we will activate a session as that user.
    2. If we cannot find a user with this “Lore-email”, we register a new user in this data store with that email, populate with the user data we got from Auth0, and activate the session.
2. If the request doesn’t come with a “Lore-email”, it’s the first time this authentication source has been used. Mind you, the actual user can be an existing user, that just pressed another button to login with this time.
    1. We now need to take all emails provided in the auth and search for all available emails (both Lore-emails and others if they exist. 
        1. If we find one match, we can get the Lore-email from that account and write back to Auth0 as the Lore-email for this new auth.
        2. If get more than one match, we are in an inconsistent state, because more than one account has the same email, when the should be unique. Preferably this cannot happen.
        3. If we get zero matches, we have to assume this is truly a new user, and we create a new account and set the new Lore-email back at Auth0.
            1. After the user logs in, we still need to make it easy for that person to understand that he might have inadvertently created a new account. Therefore, we should redirect to an account page where he can see all details and associated accounts, and prompt to add any new account.

Tricky problems
Above flow is fairly straightforward. The tricky part is that we will find that a user has created accounts with two separate emails.

Take user Adam. Adam has two emails, adam@gmail.com and adam@fb.com . He has created two users in Auth0 terms by using both of these. And until Adam somehow tells us that they belong together, we have been forced to create two separate Lore-emails and stored them in each Auth0 user.

A logical user flow is that you can simply “add” an authentication to an account. So when you are logged in as something, you press “Add account”, get redirected to Auth0, and add whatever you want. If that new auth already has a Lore-email, we initiate a merge procedure, which is tricky.

The other tricky problem is if a user changes the email within a tool using its “native” method. In this case, next time we login, we may not find the account at all, if the user doesn’t realise the discrepancy.

Should the login for be centralized through Helmgast.se or decentralized? We still need to set sessions for the actual user. De-centralized seems simpler, but then you will have to press login manually for every different app, even you logged in on another. A solution would be a link that goes via redirect to auto-login

Flarum: when not logged in, we should show link “Log in with Helmgast”. When clicked, we auto-direct to Auth0. We will pre-provision all users from Kickstarter, but will link new users to Helmgast.

How long session cookie?

Textalk: link in theme on top bar for Login with Helmgast.

3 accounts:
a@ks, lore (old orders)
a@fb, lore (article)
a@gm, flarum forum)

2 auths
a@gm
a@fb

Should be able to use any auth to get in to any account. But should also merge the lore accounts

How to securely know that the current user have access to both auth1 and auth2? If we do it in a rule, we have no knowledge of the previously logged in auth (auth1).
1. If we run the code on our server, at some point we will have auth1 in our session cookie, while receiving a token for auth2 from the redirect. At this point, we know that the user has auth to both and can merge. (Downside is that we need to run our own code here, but we pro ably have to anyway in order to provide the merge interface)
2. When we are still on auth1, we can set some token on the metadata of auth1 via auth0 API, and provide that value to the /authorize of auth2. In the rule, we can look for for an auth with that token in metadata. That means someone authorised changed the API and we can trust that the same person is now also on auth2.
3. We could provide some encrypted secret over as URL arg that belongs to auth1, and decrypt it on the rules side.
4. When still logged in as auth1, we could login again to run a rule, adding a merge=auth2 type metadata. If we then login as auth2 with merge=auth1, we can check that they point to each other. If so, we can perform the merge and delete the two temporary variables. From a user perspective, the first auth will not be noticed, as the user has SSO and is already logged in, so it will redirect immediately.
    1. Attack: a user can craft a link with a merge param, and give to another person. That user may not notice that the link includes a merge claim. But this may then plant the attacker’s email as an authorised merge param… This can be done with other merge scenarios too (send a link to /merge), but there the user has to willingly and transparently make that decision.
    2. Mitigation: Whenever we do /authorize?merge=email a rule will add an app_metadata field to the user that is: email|datetime|ip . We then lookup the other account. If the other account has the respective email, a date time that is within last 5 mins and the same IP, we can assume the same actual user is trying to merge the two accounts. If that is the case, we perform merge as below. If no merge variable at all, we do nothing (because we might just be at auth for first account at this point). If a different merge variable, we throw an error.

App_metadata:
	lore{
	  linked_emails: [email2, email3]
	}

Solution: We have to use 1 above for the time being. We go to route /merge (or /auth?merge?)

Go /authorize?link=email2&redirect=

1. As we to go /merge, we perform a redirect to achieve SSO, because we need to set a session cookie that we might not already have. We normally expect this to be immediate as the user should go to /merge only after being logged in and realising something is missing. But it’s possible the user got logged out in between, which in case, Auth0 will ask to login again. We need to here say “please login with the account you want to be your primary”. (Is that the correct statement?)
2. We display a page that says “you are authorised as.. You can link another login to this account, and we will discover any accounts you may have created with this email”. A button shows “Link account now”. This goes to a /authorize.
3. The user fills in /authorize either with email code or social and redirects back.
    1. If the new auth is same as before, display “You tried to add the same account you already have. Try again or leave to…”
    2. If the new auth is different, perform merge as below, then display: “We have linked auth 2 to auth 1. In the future, you can login with either one. If you

When we merge an account, we merge the list of linked_emails from old and new account. We then loop through that list. For each email in it, we search Auth0 for accounts with that email, and set the new metadata on it (ignoring what was there before). We could optionally ask what email is considered primary by the user, but this has no real meaning unless in scenario of 2+ below. Primary can be the first email in the list.

Whenever a user auths, we can get the linked_emails list from the auth, and check if one or more matches an account in the specific application.
If we find 0 matches:
	- Create a new user in that application, based on the first email in the list (not the email from the auth, if different)
If we find 1 match:
	- Login as that user.
If we find 2+ matches:
	- The basic way is to simply pick the first. The other account(s) will effectively be locked out. This should be logged as error for manual handling. We could potentially send an email to all involved emails informing about this.
	- The slightly more complicated is to let the user pick which email to use. This requires UI in a part of the flow where it may be hard to add UI.
	- The most complicated is to auto-merge or re-direct to a page to initiate a user led merge.

We can save in each auth the email used to login to a service. E.g:
forum: a@gm
Lore: a@fb

/auth?merge=a@fb&code=nnn

Code needs to prove we had something secret of a@fb, or anyone can take over accounts


## Migration from v0.x auth

Social users: 60%
Password: 40%
Different emails on social and pass? 30%
Login on multiple devices: 50%

Will see migration screen but already migrated:
50%

Will end up with different accounts if not migrating:

Migration procedure1:

1. Invalidate all previous sessions
2. If no "auth0_migrated" cookie AND no uid in session, redirect to migrate at login
3. When authenticated, store u2m (user to migrate) in session, then show signup form and avatar
4. At callback,
   a) if u2m exist in session, merge auth to that user and remove old auths, set auth0_migrated cookie and remove u2m
   b) if uid does not exist in session, but we have verified email in auth, merge with that account if it exists
   c) if uid does not exist and no email match, create new user
   Complete login and session.

Migration procedure2:

0. Invalidate all previous sessions
   1a) If no session, show login screen as usual
   1b) If session, do not link to login, but if accessed, show current user and message that we will add an auth
1. Login using email or social.
   3a) If current session:
   If new auth doesn't match session user, add it and show profile with updated data.
   If new auth does match session user, and
   If new auth does match session user, and user is invited, delete that user and merge to current user.
   If new auth does match session user, and user is active or deleted, report an unresolvable error and contact info@
   3b) If no current session
   If new auth matches existing user and auth is same, just login.
   If new auth matches existing user, and auth is new, add it and show profile with updated data.
   If existing user, and new auth, show a message that we added a new profile.
   4c) If existing user, and old auth, show profile and a message that user have been migrated.
   4d) If not existing user, send user to "post user" page.

If press Cancel,

Cookie includes:
email: authenticated email from auth0

Show instructions if to merge if this was unintended.

Need to always check that a user is active when verifying a logged in user, in order to be able to lock out users centrally.

How to merge:

1. We just created b@b.com (uid234) but old user is a@a.com (uid123).
2. User requests to add email a@a.com. Email verification is sent.
3. When code is entered, we will go to login but find that login for a@a.com maps to different uid123 than current session (uid234).
   But it means user controls both accounts.

4. "Enter email"
5. _Depends on user exists_
   2.1) "Welcome back NN, prove you are you"
   2.1.1) Select Google, Facebook, Password or Email Token (fine print)
   2.1.2) Optional: Provide extra details
   2.1.3) Logged in - redirect
   2.2) "Welcome to join, prove you are you"
   2.2.1) Select Google, Facebook, Password or Email Token (fine print)
   2.2.2) _Check if email verified (would only be if email same in G/FB)_
   2.2.2.1) "We need to make sure you own this email, check email"
   2.1.2) Optional: Provide extra details

## Authorization

The authorization system is there to limit access on the Lore system. It's represented in a few ways:

- Limiting access to Operations / URLs and throwing a 401 error
- Conditionally displaying links / html fragments only if the user is authorized to see it

`Resource.py` defines 8 standard operations on a resource, and they can all be generally classified as read or write operations. A certain resource can be readable by everyone or only specific groups, as well as writable. The exact logic for deciding authentication this depends on the resource.

The key to this is the function `ResourceStrategy.allowed(op, instance)` op is the current operation being tested instance refers to the specific instance of a resource, as most ops act on an instance. If the op does not act on instances (e.g. list, new), it is not needed. The user is automatically read from the`flask.g` object that keeps the current session. `allowed()` will automatically throw a `ResourceError` if the user is not allowed.

For templates, there is the macro called IS_ALLOWED() which works in a very similar way but doesn't throw exceptions and instead just outputs what's inside the macro if allowed, otherwise not.

Access to resources are normally given to groups. A group is a list of users, where there are "members" and "masters". By default, members will have read access, masters have write access, and non-members no access. Each resource has a special "group" which is the creator group, which normally means
the user who created the resource, if this is a field existing in the resource.

    Login: Create/refresh logged in session for an existing user.
    If user is not completed or if google auth works but no user, send on to verify. If user exist and auth correct, redirect to next. Otherwise throw error.

    GET:
         IF: not logged in, just show message with logout link
         ELSE: show FORM
    POST:
        IF: Logged in, just show message with logout link
        ELSE:
            IF: google_code # received google code
                connect_google
                IF success
                    IF user exists
                        login_user w/ google details
                        return JSON to redirect
                    ELSE # no user, must connect to existing user or make new
                        TBD
                ELSE
                    return JSON error
            ELIF formdata
                IF valid and user exists
                ELSE
                    return error

         ELSE: 400

    Join: Create a new user.
    Create a new user from scratch or from external auth. Create in unverified stage before email has been confirmed.

    Verify: Complete registration of a previously created but incomplete user.
    Same as join more or less, but assumes user exists but needs additional info. If email and token are given, verify user.

## Some authorization patterns

All instances can be operated by CRUD (Create, Read, Update, Delete). For some assets,
Read is split into subvarieties, e.g. Read Published, Read Unpublished.

There are 5 types of roles:

- Admin: Have full rights to modify all resources.
- Editor: Have full rights on a specific resource, and all child resources (what is a child depends)
- Reader: Have access to read specific resources regardless of their state, and to read all child resources.
- User: Have access to create new resources and read published resources.
  (When a new resource is created, that user counts as Editor of the new instance)
- Visitor: Un unauthenticated user, can only read published resources.

Subsequently, most instances have the following states:

- Draft: not published, but in various stages of edit. glyphicon glyphicon-inbox
- Revision: not used but reserved to denote older revisions of a resource glyphicon glyphicon-retweet
- Published: Published to all with general access (typically visitors) glyphicon glyphicon-eye-open
- Private: not used but reserved to mean published to selected readers only glyphicon glyphicon-eye-close
- Archived: passed published, and now hidden from general access. glyphicon glyphicon-folder-close

Public listing:

- Public listings means to show resources with Published state, created_at an earlier time (e.g. not future dated).
- An admin/editor would see all resources regardless of state and created_at.
- A reader would see Draft, Private and Published resources.

Listing: A visitor can list a resource if the Model (not resource) allows it, e.g. if it's public or not.
If the listing can be considered listing subresources of another Model, this can also be checked.

Creation: A user can by default create new resources if the Model (not resource) allows it. In addition, if the creation
of the resource creates a link to another resource, we can check that this is allowed.

## Example scenarios for authorization

/thepublisher (editor: NF, reader: PN)
/worlds
/theworld (editor: MB, reader: AW)
/articles
/thearticle (editor: PF, reader: PD)
/products
/theproduct
  
/thearticle can be read by PD, PF, FJ, MB, NF and MF but no one else regardless of status.
/thearticle can be updated/deleted by PF, MB, MF
/anewarticle can be created by MF, MB if closed, otherwise by any user
/theotherarticle can be read by anyone if published, otherwise by PF, FJ, MB, NF and MF.
For /theworld/articles:
All users, incl PD and PF, will see only published articles.
FJ, MB, NF and MF will see all articles.

For /thepublisher/articles:
All users, incl PD, PF, FJ, MB will see only published articles without worlds. However,
for articles with theworld visibility will be as previous example.
MF, NF will see all articles.

/theworld can be read by FJ, MB, NF, MF if not published, otherwise by all
/theworld can be updated/deleted by MB, MF
/anewworld can be created by MF

NF = Niklas Fröjd = niklas@helmgast.se
PN = petter@helmgast.se
MB = marco@helmgast.se
AW = anton@helmgast.se
PF = per.frojdh@gmail.com
PD = paul@helmgast.se
user = niasd@as.com

Roles: Admin, Editor, Reader, User, Visitor
Actions: Create, Read Published, Read Unpublished, Update, Delete

new: user
list: is_visitor

read: reader (also checks admin, editor)
edit: editor (also checks admin)
delete: editor


### JWT can be stored in Cookie or LocalStorage

LocalStorage:

- Pro: works regardless of domain so SSO becomes automatic.
- Con: Will not be sent with browser request, so means you need first to request page using browser, then fetch content using JS. Takes longer time and is not clean except for SPAs that does this anyway.
- Con: can be read by XSS (inserted JS on forms, etc). It’s hard to protect against.

Cookies, set to http only and secure.

- Pro: Cannot be read by XSS.
- Pro: Helps us get authenticated content in one requests, e.g. hidden pages and hidden files.
- Con: Only sent to valid domains, means we have to go through a login redirect flow (SSO) when visiting another domain.
- Con: Can only store limited data (no issue).
- Con: Can be attacked using CSRF, e.g. evilsite.com makes a request to realm.is that gets the cookie attached. Only an issue for GET/POST requests. Further investigation needed on blocking CSRF: 
