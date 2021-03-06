import pytest
from unittest import mock
import datetime
import pytz
import collections
from ..doubles import (
    MockSession,
)

from yosai.core import (
    CachingSessionStore,
    DelegatingSession,
    # ExecutorServiceSessionValidationScheduler,
    ExpiredSessionException,
    InvalidArgumentException,
    SessionEventException,
    DefaultNativeSessionHandler,
    SessionCreationException,
    StoppableScheduledExecutor,
    StoppedSessionException,
    IllegalStateException,
    InvalidSessionException,
    UnknownSessionException,
)

# ----------------------------------------------------------------------------
# SessionEventHandler
# ----------------------------------------------------------------------------


def test_seh_notify_start_publishes(session_event_handler, mock_session):
    """
    unit tested:  notify_start

    """
    seh = session_event_handler
    event_topic = 'SESSION.START'

    with mock.patch.object(seh.event_bus, 'publish') as event_publish:
        event_publish.return_value = None
        seh.notify_start(mock_session)
        event_publish.assert_called_with(event_topic,
                                         session_id=mock_session.session_id)


def test_seh_notify_start_raises(session_event_handler, mock_session, monkeypatch):
    seh = session_event_handler
    monkeypatch.delattr(mock_session, '_session_id')

    with pytest.raises(SessionEventException):
        seh.notify_start(mock_session)


def test_seh_notify_stop_publishes(session_event_handler, mock_session):
    """
    unit tested:  notify_stop
    """
    seh = session_event_handler
    event_topic = 'SESSION.STOP'

    with mock.patch.object(seh.event_bus, 'publish') as event_publish:
        event_publish.return_value = None
        seh.notify_stop('sessiontuple')
        event_publish.assert_called_with(event_topic, items='sessiontuple')


def test_seh_notify_stop_raises(session_event_handler, mock_session, monkeypatch):
    seh = session_event_handler
    monkeypatch.delattr(seh, '_event_bus')

    with pytest.raises(SessionEventException):
        seh.notify_stop(mock_session)


def test_seh_notify_expiration_publishes(session_event_handler, mock_session):
    """
    unit tested:  notify_expiration
    """
    seh = session_event_handler
    event_topic = 'SESSION.EXPIRE'

    with mock.patch.object(seh.event_bus, 'publish') as event_publish:
        event_publish.return_value = None
        seh.notify_expiration('sessiontuple')
        event_publish.assert_called_with(event_topic, items='sessiontuple')


def test_seh_notify_expiration_raises(session_event_handler, mock_session, monkeypatch):
    seh = session_event_handler
    monkeypatch.delattr(seh, '_event_bus')

    with pytest.raises(SessionEventException):
        seh.notify_expiration(mock_session)


# ----------------------------------------------------------------------------
# DefaultNativeSessionHandler
# ----------------------------------------------------------------------------

def test_sh_set_sessionstore(session_handler, mock_cache_handler, monkeypatch):
    """
    unit tested:  session_store.setter

    test case:
    the session_store property sets the attribute and calls a method
    """
    sh = session_handler
    monkeypatch.setattr(session_handler, 'cache_handler', mock_cache_handler)
    with mock.patch.object(DefaultNativeSessionHandler,
                           'apply_cache_handler_to_session_store') as achss:
        achss.return_value = None

        sh.session_store = 'sessionstore'

        achss.assert_called_once_with()


def test_sh_set_cache_handler(session_handler):
    """
    unit tested:  cache_handler.setter

    test case:
    the cache_handler property sets the attribute and calls a method
    """
    sh = session_handler

    with mock.patch.object(DefaultNativeSessionHandler,
                           'apply_cache_handler_to_session_store') as achss:
        achss.return_value = None

        sh.cache_handler = 'cache_handler'

        achss.assert_called_once_with()


def test_sh_achtsd(
        session_handler, monkeypatch, caching_session_store):
    """
    unit tested:  apply_cache_handler_to_session_store

    test case:
    when a sessionStore is configured, the sessionStore sets the cachehandler
    """
    sh = session_handler

    monkeypatch.setattr(sh, '_cache_handler', 'cachehandler')
    monkeypatch.setattr(sh, '_session_store', caching_session_store)
    sh.apply_cache_handler_to_session_store()
    assert sh.session_store.cache_handler == 'cachehandler'


def test_sh_achtsd_raises(
        session_handler, monkeypatch, caching_session_store):
    """
    unit tested:  apply_cache_handler_to_session_store

    test case:
    if no sessionStore configured, will return gracefully
    """
    sh = session_handler
    monkeypatch.setattr(sh, '_cache_handler', 'cachehandler')
    monkeypatch.delattr(caching_session_store, '_cache_handler')
    monkeypatch.setattr(sh, '_session_store', caching_session_store)
    sh.apply_cache_handler_to_session_store()


def test_sh_eventbus_passthrough_setter(session_handler):
    sh = session_handler
    sh.event_bus = 'event_bus'
    assert (sh.session_event_handler.event_bus == 'event_bus'
            and sh.event_bus == sh.session_event_handler.event_bus)


def test_sh_create_session(
        session_handler, monkeypatch, caching_session_store):
    sh = session_handler
    monkeypatch.setattr(caching_session_store, 'create', lambda x: x)
    monkeypatch.setattr(sh, '_session_store', caching_session_store)
    result = sh.create_session('session')
    assert result == 'session'


def test_sh_delete(
        session_handler, monkeypatch, caching_session_store):
    sh = session_handler
    monkeypatch.setattr(sh, '_session_store', caching_session_store)
    with mock.patch.object(CachingSessionStore, 'delete') as css_del:
        css_del.return_value = None
        sh.delete('session')
        css_del.assert_called_once_with('session')


def test_sh_retrieve_session_w_sessionid_raising(
        session_handler, monkeypatch, caching_session_store, session_key):
    """
    unit tested:  retrieve_session

    test case:
    when no session can be retrieved from a data source when using a sessionid,
    an exception is raised
    """
    sh = session_handler
    css = caching_session_store

    monkeypatch.setattr(css, 'read', lambda x: None)
    monkeypatch.setattr(sh, '_session_store', css)

    with pytest.raises(UnknownSessionException):
        sh._retrieve_session(session_key)


def test_sh_retrieve_session_withsessionid_returning(
        session_handler, monkeypatch, caching_session_store, session_key):
    """
    unit tested:  retrieve_session

    test case:
    retrieves session from a data source, using a sessionid as parameter,
    and returns it
    """
    sh = session_handler
    css = caching_session_store

    monkeypatch.setattr(css, 'read', lambda x: x)
    monkeypatch.setattr(sh, '_session_store', css)

    result = sh._retrieve_session(session_key)
    assert result == 'sessionid123'


def test_sh_retrieve_session_withoutsessionid(
        session_handler, monkeypatch, caching_session_store, session_key):
    """
    unit tested:  retrieve_session

    test case:
    fails to obtain a session_id value from the sessionkey, returning None
    """
    sh = session_handler

    monkeypatch.setattr(session_key, 'session_id', None)

    result = sh._retrieve_session(session_key)
    assert result is None


def test_sh_dogetsession_none(session_handler, monkeypatch, session_key):
    """
    unit tested: do_get_session

    test case:
    - retrieve_session fails to returns a session, returning None
    """
    sh = session_handler

    monkeypatch.setattr(sh, '_retrieve_session', lambda x: None)

    result = sh.do_get_session(session_key)
    assert result is None


def test_sh_dogetsession_notouch(session_handler, monkeypatch, session_key):
    """
    unit tested: do_get_session

    test case:
    - retrieve_session returns a session
    - validate will be called
    - auto_touch is False by default, so skipping its clode block
    - session is returned
    """
    sh = session_handler

    monkeypatch.setattr(sh, '_retrieve_session', lambda x: 'session')

    with mock.patch.object(DefaultNativeSessionHandler, 'validate') as sh_validate:
        sh_validate.return_value = None

        result = sh.do_get_session(session_key)
        sh_validate.assert_called_once_with('session', session_key)
        assert result == 'session'


def test_sh_dogetsession_touch(
        session_handler, monkeypatch, session_key, mock_session):
    """
    unit tested: do_get_session

    test case:
    - retrieve_session returns a session
    - validate will be called
    - auto_touch is set True, so its clode block is called
    - session is returned
    """
    sh = session_handler

    monkeypatch.setattr(sh, '_retrieve_session', lambda x: mock_session)
    monkeypatch.setattr(sh, 'auto_touch', True)

    with mock.patch.object(DefaultNativeSessionHandler, 'validate') as sh_validate:
        sh_validate.return_value = None
        with mock.patch.object(DefaultNativeSessionHandler, 'on_change') as oc:
            oc.return_value = None
            with mock.patch.object(mock_session, 'touch') as ms_touch:
                ms_touch.return_value = None

                result = sh.do_get_session(session_key)

                sh_validate.assert_called_once_with(mock_session, session_key)
                ms_touch.assert_called_once_with()
                oc.assert_called_once_with(mock_session)

                assert result == mock_session


def test_sh_validate_succeeds(session_handler, mock_session, monkeypatch,
                              session_key):
    """
    unit test:  validate

    test case:
    basic code path exercise
    """
    sh = session_handler

    with mock.patch.object(mock_session, 'validate') as sessval:
        sessval.return_value = None
        sh.validate(mock_session, 'sessionkey123')


def test_sh_validate_expired(session_handler, mock_session, monkeypatch,
                             session_key):
    """
    unit test:  validate

    test case:
    do_validate raises expired session exception, calling on_expiration and
    raising
    """
    sh = session_handler

    with mock.patch.object(mock_session, 'validate') as ms_dv:
        ms_dv.side_effect = ExpiredSessionException
        with mock.patch.object(DefaultNativeSessionHandler, 'on_expiration') as sh_oe:
            sh_oe.return_value = None
            with pytest.raises(ExpiredSessionException):

                sh.validate(mock_session, 'sessionkey123')

                sh_oe.assert_called_once_with(mock_session,
                                              ExpiredSessionException,
                                              'sessionkey123')

def test_sh_validate_invalid(session_handler, mock_session, monkeypatch,
                             session_key):
    """
    unit test:  validate

    test case:
    do_validate raises expired session exception, calling on_expiration and
    raising
    """
    sh = session_handler

    with mock.patch.object(mock_session, 'validate') as ms_dv:
        ms_dv.side_effect = StoppedSessionException
        with mock.patch.object(DefaultNativeSessionHandler, 'on_invalidation') as sh_oe:
            sh_oe.return_value = None
            with pytest.raises(InvalidSessionException):

                sh.validate(mock_session, 'sessionkey123')

                sh_oe.assert_called_once_with(mock_session,
                                              ExpiredSessionException,
                                              'sessionkey123')


def test_sh_on_stop(session_handler, mock_session, monkeypatch):
    """
    unit tested:  on_stop

    test case:
    updated last_access_time and calls on_change
    """
    sh = session_handler
    monkeypatch.setattr(mock_session, '_last_access_time', 'anything')
    monkeypatch.setattr(mock_session, '_stop_timestamp', None, raising=False)
    monkeypatch.setattr(mock_session, '_stop_timestamp',
                        datetime.datetime.now(pytz.utc))
    with mock.patch.object(sh, 'on_change') as mock_onchange:
        sh.on_stop(mock_session)
        mock_onchange.assert_called_with(mock_session)
        assert mock_session.last_access_time == mock_session.stop_timestamp


def test_sh_after_stopped(session_handler, monkeypatch):
    """
    unit tested:  after_stopped

    test case:
    if delete_invalid_sessions is True, call delete method
    """
    sh = session_handler
    monkeypatch.setattr(sh, 'delete_invalid_sessions', True)
    with mock.patch.object(sh, 'delete') as sh_delete:
        sh_delete.return_value = None
        sh.after_stopped('session')
        sh_delete.assert_called_once_with('session')


def test_sh_on_expiration(session_handler, monkeypatch, mock_session):
    """
    unit tested:  on_expiration

    test case:
    set's a session to expired and then calls on_change
    """
    sh = session_handler
    with mock.patch.object(sh, 'on_change') as sh_oc:
        sh_oc.return_value = None
        sh.on_expiration(mock_session)
        sh_oc.assert_called_once_with(mock_session)


@pytest.mark.parametrize('ese,session_key',
                         [('ExpiredSessionException', None),
                          (None, 'sessionkey123')])
def test_sh_on_expiration_onenotset(session_handler, ese, session_key):
    """
    unit tested:  on_expiration

    test case:
        expired_session_exception or session_key are set, but not both
    """
    sh = session_handler

    with pytest.raises(InvalidArgumentException):
        sh.on_expiration(session='testsession',
                         expired_session_exception=ese,
                         session_key=session_key)


def test_sh_on_expiration_allset(session_handler, mock_session, monkeypatch):
    """
    unit tested:  on_expiration

    test case:
        all parameters are passed, calling on_change, notify_expiration, and
        after_expired
    """
    sh = session_handler

    session_tuple = collections.namedtuple(
        'session_tuple', ['identifiers', 'session_key'])
    mysession = session_tuple('identifiers', 'sessionkey123')
    monkeypatch.setattr(mock_session, 'get_internal_attribute',
                        lambda x: 'identifiers')

    with mock.patch.object(sh.session_event_handler, 'notify_expiration') as sh_ne:
        sh_ne.return_value = None
        with mock.patch.object(sh, 'after_expired') as sh_ae:
            sh_ae.return_value = None
            with mock.patch.object(sh, 'on_change') as sh_oc:
                sh_oc.return_value = None

                sh.on_expiration(session=mock_session,
                                 expired_session_exception='ExpiredSessionException',
                                 session_key='sessionkey123')

                sh_ne.assert_called_once_with(mysession)
                sh_ae.assert_called_once_with(mock_session)
                sh_oc.assert_called_once_with(mock_session)


def test_sh_after_expired(session_handler, monkeypatch):
    """
    unit tested:  after_expired

    test case:
    when delete_invalid_sessions is True, invoke delete method
    """
    sh = session_handler
    monkeypatch.setattr(sh, 'delete_invalid_sessions', True)
    with mock.patch.object(sh, 'delete') as sh_del:
        sh_del.return_value = None

        sh.after_expired('session')

        sh_del.assert_called_once_with('session')


def test_sh_on_invalidation_esetype(session_handler, mock_session):
    """
    unit tested:  on_invalidation

    test case:
        when an exception of type ExpiredSessionException is passed,
        on_expiration is called and then method returns
    """
    sh = session_handler
    ise = ExpiredSessionException('testing')
    session_key = 'sessionkey123'
    with mock.patch.object(sh, 'on_expiration') as mock_oe:
        sh.on_invalidation(session=mock_session, ise=ise, session_key=session_key)
        mock_oe.assert_called_with


def test_sh_on_invalidation_isetype(
        session_handler, mock_session, monkeypatch):
    """
    unit tested:  on_invalidation

    test case:
        when an exception NOT of type ExpiredSessionException is passed,
        an InvalidSessionException higher up the hierarchy is assumed
        and on_stop, notify_stop, and after_stopped are called
    """
    sh = session_handler
    ise = StoppedSessionException('testing')
    session_key = 'sessionkey123'

    session_tuple = collections.namedtuple(
        'session_tuple', ['identifiers', 'session_key'])
    mysession = session_tuple('identifiers', 'sessionkey123')

    monkeypatch.setattr(mock_session, 'get_internal_attribute',
                        lambda x: 'identifiers')

    with mock.patch.object(sh, 'on_stop') as mock_onstop:
        mock_onstop.return_value = None

        with mock.patch.object(sh.session_event_handler,
                               'notify_stop') as mock_ns:
            mock_ns.return_value = None

            with mock.patch.object(sh, 'after_stopped') as mock_as:
                mock_as.return_value = None

                sh.on_invalidation(session=mock_session,
                                   ise=ise,
                                   session_key=session_key)

                mock_onstop.assert_called_once_with(mock_session)
                mock_ns.assert_called_once_with(mysession)
                mock_as.assert_called_once_with(mock_session)


def test_sh_on_change(session_handler, monkeypatch, caching_session_store):
    """
    unit tested:  on_change

    test case:
    passthrough call to session_store.update
    """
    sh = session_handler
    monkeypatch.setattr(sh, '_session_store', caching_session_store)
    with mock.patch.object(sh._session_store, 'update') as ss_up:
        ss_up.return_value = None

        sh.on_change('session')

        ss_up.assert_called_once_with('session')


# ------------------------------------------------------------------------------
# DefaultNativeSessionManager
# ------------------------------------------------------------------------------

def test_nsm_sessioneventhandler_setter(
        default_native_session_manager, session_event_handler):
    """
    test case:
    setting the session_event_handler attribute and setter-injecting it into
    the session_handler attribute
    """
    nsm = default_native_session_manager
    nsm.session_event_handler = session_event_handler
    assert nsm.session_handler.session_event_handler == session_event_handler


def test_nsm_eventbus_setter(
        default_native_session_manager, session_event_handler):
    """
    test case:
    setting the event_bus attribute and setter-injecting it into
    the session_handler attribute
    """
    nsm = default_native_session_manager
    nsm.event_bus = 'event_bus1'
    assert (nsm._event_bus == 'event_bus1' and
            nsm.session_handler.session_event_handler.event_bus == 'event_bus1')


def test_nsm_start(default_native_session_manager, monkeypatch):
    """
    unit tested:  start

    test case:
    verify that start calls other methods
    """
    nsm = default_native_session_manager
    dumbsession = type('DumbSession', (object,), {'session_id': '1234'})()
    monkeypatch.setattr(nsm, '_create_session', lambda x: dumbsession)
    monkeypatch.setattr(nsm, 'create_exposed_session', lambda session=None, context=None: dumbsession)

    with mock.patch.object(nsm.session_handler, 'on_start') as mock_os:
        mock_os.return_value = None
        with mock.patch.object(nsm.session_event_handler, 'notify_start') as ns:
            ns.return_value = None
            result = nsm.start('session_context')

            mock_os.assert_called_once_with(dumbsession, 'session_context')
            ns.assert_called_once_with(dumbsession)
            assert result == dumbsession


def test_nsm_stop(
        default_native_session_manager, monkeypatch, mock_session, session_key):
    """
    unit tested:  stop

    test case:
    basic method exercise, calling methods and completing
    """
    nsm = default_native_session_manager

    session_tuple = collections.namedtuple(
        'session_tuple', ['identifiers', 'session_key'])
    mysession = session_tuple('identifiers', 'sessionkey123')
    monkeypatch.setattr(mock_session, 'get_internal_attribute',
                        lambda x: 'identifiers')

    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)

    with mock.patch.object(MockSession, 'stop') as stop:
        stop.return_value = None
        with mock.patch.object(nsm.session_handler, 'on_stop') as on_stop:
            on_stop.return_value = None
            with mock.patch.object(nsm.session_event_handler, 'notify_stop') as notify_stop:
                notify_stop.return_value = None
                with mock.patch.object(nsm.session_handler, 'after_stopped') as after_stopped:
                    after_stopped.return_value = None

                    nsm.stop('sessionkey123', 'identifiers')

                    stop.assert_called_with()
                    on_stop.assert_called_with(mock_session)
                    notify_stop.assert_called_with(mysession)
                    after_stopped.assert_called_with(mock_session)


def test_nsm_stop_raises(
        default_native_session_manager, mock_session, monkeypatch):
    """
    unit tested:  stop

    test case:
    exception is raised and finally section is executed
    """
    nsm = default_native_session_manager

    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)
    with mock.patch.object(MockSession, 'stop') as stop:
        stop.side_effect = InvalidSessionException
        with mock.patch.object(nsm.session_handler,
                               'after_stopped') as after_stopped:
            with pytest.raises(InvalidSessionException):
                nsm.stop('sessionkey123', 'identifiers')
                after_stopped.assert_called_with(mock_session)


def test_nsm_create_session(
        default_native_session_manager, monkeypatch, mock_session):
    nsm = default_native_session_manager

    monkeypatch.setattr(nsm.session_factory, 'create_session', lambda x: mock_session)
    monkeypatch.setattr(nsm.session_handler, 'create_session', lambda x: 'sessionid123')

    result = nsm._create_session('sessioncontext')
    assert result == mock_session


def test_nsm_create_session_raises(
        default_native_session_manager, monkeypatch, mock_session):
    nsm = default_native_session_manager

    monkeypatch.setattr(nsm.session_factory, 'create_session', lambda x: mock_session)
    monkeypatch.setattr(nsm.session_handler, 'create_session', lambda x: None)

    with pytest.raises(SessionCreationException):
        nsm._create_session('sessioncontext')


def test_nsm_create_exposed_session(default_native_session_manager):
    """
    unit tested:  create_exposed_session

    test case:
    basic codepath exercise
    """
    nsm = default_native_session_manager
    dumbsession = type('DumbSession', (object,), {'session_id': '1234'})()
    result = nsm.create_exposed_session(dumbsession)
    assert isinstance(result, DelegatingSession)


def test_nsm_get_session_locates(default_native_session_manager, monkeypatch):
    """
    unit tested: get_session

    test case:
    lookup_session returns a session, and so create_exposed_session is called
    with it
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(nsm.session_handler,
                        'do_get_session', lambda x: x)
    monkeypatch.setattr(nsm, 'create_exposed_session', lambda x, y: x)

    results = nsm.get_session('key')

    assert results == 'key'  # asserts that it was called


def test_nsm_get_session_doesnt_locate(
        default_native_session_manager, monkeypatch):
    """
    unit tested:  get_session

    test case:
    lookup session fails to locate a session and so None is returned
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(nsm.session_handler, 'do_get_session', lambda x: None)
    results = nsm.get_session('key')

    assert results is None


def test_nsm_lookup_required_session_locates(
        default_native_session_manager, monkeypatch):
    """
    unit tested:  lookup_required_session

    test case:
    lookup_session finds and returns a session
    """
    nsm = default_native_session_manager

    monkeypatch.setattr(nsm.session_handler, 'do_get_session', lambda x: 'session')
    results = nsm._lookup_required_session('key')
    assert results == 'session'


def test_nsm_lookup_required_session_failstolocate(
        default_native_session_manager, monkeypatch):
    """
    unit tested:  lookup_required_session

    test case:
    lookup_session fails to locate a session, raising an exception instead
    """
    nsm = default_native_session_manager

    monkeypatch.setattr(nsm.session_handler, 'do_get_session', lambda x: None)
    with pytest.raises(UnknownSessionException):
        nsm._lookup_required_session('key')


def test_nsm_is_valid(default_native_session_manager):
    """
    unit tested:  is_valid

    test case:
    a valid sesion returns True
    """
    nsm = default_native_session_manager

    with mock.patch.object(nsm, 'check_valid') as mocky:
        mocky.return_value = True
        result = nsm.is_valid('sessionkey123')
        assert result


def test_nsm_is_valid_raisefalse(default_native_session_manager):
    """
    unit tested:  is_valid

    test case:
    an invalid sesion returns False
    """
    nsm = default_native_session_manager

    with mock.patch.object(nsm, 'check_valid') as mocky:
        mocky.side_effect = InvalidSessionException
        result = nsm.is_valid('sessionkey123')
        assert result is False


def test_nsm_check_valid_raises(default_native_session_manager):
    """
    unit tested:  check_valid

    test case:
    calls lookup_required_session
    """
    nsm = default_native_session_manager
    with mock.patch.object(nsm, '_lookup_required_session') as mocky:
        mock.return_value = None
        nsm.check_valid('sessionkey123')
        mocky.assert_called_with('sessionkey123')


def test_nsm_get_start_timestamp(
        default_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  get_start_timestamp

    test case:
    basic code exercise, passes through and returns
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(mock_session, '_start_timestamp', 'starttime')
    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)
    results = nsm.get_start_timestamp('sessionkey')
    assert results == mock_session.start_timestamp


def test_nsm_get_last_access_time(
        default_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  get_last_access_time

    test case:
    basic code exercise, passes through and returns
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(mock_session, '_last_access_time', 'lasttime')
    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)
    results = nsm.get_last_access_time('sessionkey')
    assert results == mock_session.last_access_time


def test_nsm_get_absolute_timeout(
        default_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  get_absolute_timeout

    test case:
    basic code exercise, passes through and returns
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(mock_session, '_absolute_timeout', 'abstimeout')
    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)
    results = nsm.get_absolute_timeout(mock_session)
    assert results == 'abstimeout'


def test_nsm_get_idle_timeout(
        default_native_session_manager, monkeypatch, mock_session):
    """
    unit tested: get_idle_timeout

    test case:
    basic code exercise, passes through and returns
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(mock_session, '_idle_timeout', 'idletimeout')
    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)
    results = nsm.get_idle_timeout(mock_session)
    assert results == 'idletimeout'


def test_nsm_set_idle_timeout(
        default_native_session_manager, monkeypatch, mock_session):
    """
    unit tested: set_idle_timeout

    test case:
    basic code exercise, passes through and returns
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)

    with mock.patch.object(nsm.session_handler, 'on_change') as mocky:
        mocky.return_value = None
        nsm.set_idle_timeout('sessionkey123', 'timeout')
        mocky.assert_called_once_with(mock_session)
        assert mock_session.idle_timeout == 'timeout'


def test_nsm_set_absolute_timeout(
        default_native_session_manager, monkeypatch, mock_session):
    """
    unit tested: set_absolute_timeout

    test case:
    basic code exercise, passes through and returns
    """
    nsm = default_native_session_manager

    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)

    with mock.patch.object(nsm.session_handler, 'on_change') as mocky:
        mocky.return_value = None
        nsm.set_absolute_timeout('sessionkey123', 'timeout')
        mocky.assert_called_once_with(mock_session)
        assert mock_session.absolute_timeout == 'timeout'


def test_nsm_touch(default_native_session_manager, mock_session, monkeypatch):
    """
    unit tested:  touch

    test case:
    basic code exercise, passes through
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)
    with mock.patch.object(nsm.session_handler, 'on_change') as mocky:
        mocky.return_value = None
        with mock.patch.object(MockSession, 'touch') as touchy:
            nsm.touch('sessionkey123')
            touchy.assert_called_once_with()
            mocky.assert_called_once_with(mock_session)


def test_nsm_get_host(default_native_session_manager, mock_session, monkeypatch):
    """
    unit tested:  get_host

    test case:
    basic code exercise, passes through and returns host
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)
    with mock.patch.object(nsm.session_handler, 'on_change') as mocky:
        mocky.return_value = None
        result = nsm.get_host('sessionkey123')
        assert result == '127.0.0.1'


def test_nsm_get_internal_attribute_keys_results(
        default_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  get_internal_attribute_keys

    test case:
    basic code exercise, passes through and returns a tuple contains 3 mock items
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(mock_session, '_internal_attribute_keys',
                        ['one', 'two'], raising=False)
    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)
    result = nsm.get_internal_attribute_keys('sessionkey123')
    assert result == tuple(['one', 'two'])


def test_nsm_get_internal_attribute_keys_empty(
        default_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  get_internal_attribute_keys

    test case:
    basic code exercise, passes through and returns an empty tuple
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(mock_session, '_internal_attribute_keys', [], raising=False)
    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)
    result = nsm.get_internal_attribute_keys('sessionkey123')
    assert result == tuple()


def test_nsm_get_internal_attribute(
        default_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  get_internal_attribute

    test case:
    basic code exercise, passes through and returns an internal_attribute
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(mock_session, 'get_internal_attribute', lambda x: 'attr')
    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)
    result = nsm.get_internal_attribute('sessionkey123','anything')
    assert result == 'attr'


def test_nsm_set_internal_attribute(
        default_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  set_internal_attribute

    test case:
    sets an internal_attribute
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)
    with mock.patch.object(nsm.session_handler, 'on_change') as mocky:
        mocky.return_value = None
        with mock.patch.object(mock_session, 'set_internal_attribute') as sia:
            sia.return_value = None

            nsm.set_internal_attribute('sessionkey123',
                                       attribute_key='attr321', value=321)

            sia.assert_called_once_with('attr321', 321)
            mocky.assert_called_once_with(mock_session)


def test_nsm_set_internal_attribute_removes(
        default_native_session_manager):
    """
    unit tested:  set_internal_attribute

    test case:
    calling set_internal_attribute without a value results in the removal of an internal_attribute
    """
    nsm = default_native_session_manager

    with mock.patch.object(nsm, 'remove_internal_attribute') as mock_ra:
        nsm.set_internal_attribute('sessionkey123', attribute_key='attr1')
        mock_ra.assert_called_once_with('sessionkey123', 'attr1')


def test_nsm_remove_internal_attribute(
        default_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  remove_internal_attribute

    test case:
    successfully removes an internal_attribute
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(mock_session, 'remove_internal_attribute', lambda x: 'attr1')
    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)
    with mock.patch.object(nsm.session_handler, 'on_change') as mocky:
        mocky.return_value = None

        result = nsm.remove_internal_attribute('sessionkey123',
                                               attribute_key='attr321')

        mocky.assert_called_once_with(mock_session)
        assert result == 'attr1'


def test_nsm_remove_internal_attribute_nothing(
        default_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  remove_internal_attribute

    test case:
    removing an internal_attribute that doesn't exist returns None
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)
    with mock.patch.object(nsm.session_handler, 'on_change') as mocky:
        mocky.return_value = None

        result = nsm.remove_internal_attribute('sessionkey123',
                                               attribute_key='attr321')

        assert result is None


def test_nsm_get_attribute_keys_results(
        default_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  get_attribute_keys

    test case:
    basic code exercise, passes through and returns a tuple contains 3 mock items
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(mock_session, '_attribute_keys',
                        ['one', 'two'], raising=False)
    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)
    result = nsm.get_attribute_keys('sessionkey123')
    assert result == tuple(['one', 'two'])


def test_nsm_get_attribute_keys_empty(
        default_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  get_attribute_keys

    test case:
    basic code exercise, passes through and returns an empty tuple
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(mock_session, '_attribute_keys', [], raising=False)
    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)
    result = nsm.get_attribute_keys('sessionkey123')
    assert result == tuple()


def test_nsm_get_attribute(
        default_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  get_attribute

    test case:
    basic code exercise, passes through and returns an attribute
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(mock_session, 'get_attribute', lambda x: 'attr')
    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)
    result = nsm.get_attribute('sessionkey123','anything')
    assert result == 'attr'


def test_nsm_set_attribute(
        default_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  set_attribute

    test case:
    sets an attribute
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)
    with mock.patch.object(nsm.session_handler, 'on_change') as mocky:
        mocky.return_value = None
        with mock.patch.object(mock_session, 'set_attribute') as sia:
            sia.return_value = None

            nsm.set_attribute('sessionkey123',
                              attribute_key='attr321', value=321)

            sia.assert_called_once_with('attr321', 321)
            mocky.assert_called_once_with(mock_session)


def test_nsm_set_attribute_removes(
        default_native_session_manager):
    """
    unit tested:  set_attribute

    test case:
    calling set_attribute without a value results in the removal of an attribute
    """
    nsm = default_native_session_manager

    with mock.patch.object(nsm, 'remove_attribute') as mock_ra:
        nsm.set_attribute('sessionkey123', attribute_key='attr1')
        mock_ra.assert_called_once_with('sessionkey123', 'attr1')


def test_nsm_remove_attribute(
        default_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  remove_attribute

    test case:
    successfully removes an attribute
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(mock_session, 'remove_attribute', lambda x: 'attr1')
    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)
    with mock.patch.object(nsm.session_handler, 'on_change') as mocky:
        mocky.return_value = None

        result = nsm.remove_attribute('sessionkey123',
                                      attribute_key='attr321')

        mocky.assert_called_once_with(mock_session)
        assert result == 'attr1'


def test_nsm_remove_attribute_nothing(
        default_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  remove_attribute

    test case:
    removing an attribute that doesn't exist returns None
    """
    nsm = default_native_session_manager
    monkeypatch.setattr(nsm, '_lookup_required_session', lambda x: mock_session)
    with mock.patch.object(nsm.session_handler, 'on_change') as mocky:
        mocky.return_value = None

        result = nsm.remove_attribute('sessionkey123',
                                      attribute_key='attr321')

        assert result is None
