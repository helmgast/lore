function autolink(user, context, callback) {
  const Sentry = require('@sentry/node@5.15.5');
  Sentry.init({ dsn: "https://18af24f075334fb786cb19d44649dd59@sentry.io/1432994", serverName: "auth0.rules.auto-link" });
  Sentry.setUser({ id: user.user_id, email: user.email });
  Sentry.setContext("extra", { user: user, context: context });
  let msg = '';

  function logError(msg, id) {
    console.log(`ERROR for ${id}: ${msg}`);
    Sentry.captureException(msg);
  }

  if (!user.email || !user.email_verified || context.primaryUser || user.identities.length > 1) {
    // No email or already linked
    console.log(`Already linked or not ready`);
    return callback(null, user, context);
  } else {
    let ManagementClient, management;
    try {
      ManagementClient = require('auth0@2.27.1').ManagementClient;
      management = new ManagementClient({
        token: auth0.accessToken,
        domain: auth0.domain
      });
      Sentry.setContext("extra", { ManagementClient, management });
      management.getUsersByEmail(user.email)
        .then((data) => {
          data = data.filter(function (u) {
            return u.email_verified && (u.user_id !== user.user_id);
          });
          if (data.length > 0) {

            let payload = { user_id: user.identities[0].user_id, provider: user.identities[0].provider };
            management.linkUsers(data[0].user_id, payload).then(() => {
              console.log(`Successfully linked this user ${user.user_id} to ${data[0].user_id}`);
              context.primaryUser = data[0].user_id;
              callback(null, user, context);
            }).catch((err) => {
              msg = `Error linking ${user.user_id} to ${data[0].user_id}, ${err}`;
              logError(msg, user.user_id);
              callback(new Error(msg));
            });
            if (data.length > 1) {
              msg = `We didn't expect more than one primaries already ${data.map(e => `${e.email}|${e.user_id}`)}`;
              logError(msg, user.user_id);
            }
          } else {
            console.log("Nothing to link to yet");
            callback(null, user, context);
          }
        })
        .catch((err) => {
          msg = `Error getting emails for ${user.email}, ${err}`;
          logError(msg, user.user_id);
          callback(new Error(msg));
        });
    } catch (e) {
      Sentry.captureException(e);
      callback(e);
    }
  }
}