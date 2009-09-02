#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import types, sys
import web
from web import render
from web import iredconfig as cfg
from controllers.ldap import base
from controllers.ldap.basic import dbinit
from libs.ldaplib import domain, user, iredldif, ldaputils

session = web.config.get('_session')

domainLib = domain.Domain()
userLib = user.User()

#
# User related.
#
class list(dbinit):
    def __del__(self):
        pass

    @base.protected
    def GET(self, domain=''):
        domain = web.safestr(domain.split('/', 1)[0])
        allDomains = domainLib.list(attrs=['domainName'])

        if domain == '' or domain is None:
            #return render.users(allDomains=allDomains)

            # List users if only one domain available.
            if isinstance(allDomains, types.ListType) is True and len(allDomains) == 1:
                cur_domain = str(allDomains[0][1]['domainName'][0])
                result = userLib.list(domain=cur_domain)
                if result[0] is True:
                    web.seeother('/users/' + cur_domain)
                else:
                    web.seeother('/domains?msg=%s' % result[1] )
            elif isinstance(allDomains, types.ListType) is True and len(allDomains) == 0:
                return render.users(msg='NO_DOMAIN_AVAILABLE')
            elif isinstance(allDomains, types.ListType) is True and len(allDomains) > 1:
                return render.users(allDomains=allDomains)
            else:
                web.seeother('/domains?msg=NO_SUCH_DOMAIN')
        else:
            result = userLib.list(domain=domain)
            if result[0] is True:
                return render.users(
                        users=result[1], cur_domain=domain,
                        allDomains=allDomains,
                        msg=None,
                        )
            else:
                web.seeother('/domains?msg=%s' % result[1])

    @base.protected
    def POST(self, domain):
        i = web.input(_unicode=False, mail=[])
        mails = i.mail
        result = userLib.delete(mails=mails)
        web.seeother('/users/' + str(domain))

class profile(dbinit):
    @base.protected
    def GET(self, profile_type, mail):
        i = web.input(enabledService=[], telephoneNumber=[],)
        self.mail = web.safestr(mail)
        self.profile_type = web.safestr(profile_type)

        if len(self.mail.split('@', 1)) == 2 and \
                self.profile_type in ['general', 'shadow', 'groups', 'services', 'forwarding', 'bcc', 'password', 'advanced',]:
            self.domain = self.mail.split('@', 1)[1]

            self.profile = userLib.profile(mail=self.mail)
            if self.profile:
                return render.user_profile(
                        profile_type=self.profile_type,
                        mail=self.mail,
                        user_profile=self.profile,
                        min_passwd_length=cfg.general.get('min_passwd_length'),
                        max_passwd_length=cfg.general.get('max_passwd_length'),
                        msg=i.get('msg', None)
                        )
            else:
                web.seeother('/users/' + '?msg=PERMISSION_DENIED')
        else:
            web.seeother('/domains?msg=INVALID_REQUEST')

    @base.protected
    def POST(self, profile_type, mail):
        i = web.input(enabledService=[], telephoneNumber=[],)
        self.profile_type = web.safestr(profile_type)
        self.mail = web.safestr(mail)

        self.result = userLib.update(
                profile_type=self.profile_type,
                mail=self.mail,
                data=i,
                )
        if self.result is True:
            web.seeother('/profile/user/%s/%s?msg=UPDATED_SUCCESS' % (self.profile_type, self.mail))
        elif self.result[0] is False:
            web.seeother('/profile/user/%s/%s?msg=%s' % (self.profile_type, self.mail, self.result[1]))

class create(dbinit):
    @base.protected
    def GET(self, domainName=None):
        if domainName is None:
            self.domain = ''
        else:
            self.domain = web.safestr(domainName)

        return render.user_create(
                domain=self.domain,
                allDomains=domainLib.list(),
                default_quota=domainLib.getDomainDefaultUserQuota(self.domain),
                )

    @base.protected
    def POST(self):
        i = web.input()

        # Get domain name, username, cn.
        self.domain = i.get('domainName', None)
        self.username = i.get('username', None)

        if self.domain is None or self.username is None:
            return render.user_create(
                    domain=self.domain,
                    allDomains=domainLib.list(),
                    default_quota=domainLib.getDomainDefaultUserQuota(self.domain),
                    )

        cn = i.get('cn', None)
        quota = i.get('quota', default_quota=domainLib.getDomainDefaultUserQuota(self.domain))

        # Check password.
        newpw = web.safestr(i.get('newpw'))
        confirmpw = web.safestr(i.get('confirmpw'))
        if len(newpw) > 0 and len(confirmpw) > 0 and newpw == confirmpw:
            passwd = ldaputils.generatePasswd(newpw, pwscheme=cfg.general.get('default_pw_scheme', 'SSHA'))
        else:
            return render.user_create(
                    domain=self.domain,
                    allDomains=domainLib.list(),
                    username=self.username,
                    default_quota=domainLib.getDomainDefaultUserQuota(self.domain),
                    cn=cn,
                    msg='PW_ERROR',
                    )

        ldif = iredldif.ldif_mailuser(
                domain=web.safestr(self.domain),
                username=web.safestr(self.username),
                cn=cn,
                passwd=passwd,
                quota=quota,
                )

        dn = ldaputils.convEmailToUserDN(self.username + '@' + domain)
        result = userLib.add(dn, ldif)
        if result is True:
            web.seeother('/profile/user/general/' + self.username + '@' + self.domain + '?msg=CREATE_SUCCESS')
        elif result == 'ALREADY_EXISTS':
            web.seeother('/users/' + self.domain + '?msg=ALREADY_EXISTS')
        else:
            web.seeother('/users/' + self.domain)

class delete(dbinit):
    @base.protected
    def POST(self):
        i = web.input(mail=[])
        domain = i.get('domain', None)
        if domain is None:
            web.seeother('/users?msg=NO_DOMAIN')

        mails = i.get('mail', [])
        for mail in mails:
            dn = ldap.filter.escape_filter_chars(ldaputils.convEmailToUserDN(mail))
        web.seeother('/users/' + web.safestr(domain))
