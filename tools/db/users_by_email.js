var email = "froejd@gmail.com";
db.getCollection('user').find({
    $or: [
        {email:email},
        {"identities.profileData.email": new RegExp("^"+email+"$","i")},
        {"auth_keys":new RegExp("^"+email+"\\|","i")}
        ]})