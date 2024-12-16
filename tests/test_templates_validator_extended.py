import pytest
from dns_services_gateway.templates.records.validator import RecordValidator
from dns_services_gateway.templates.models.base import RecordModel
from dns_services_gateway.records import RecordType
from dns_services_gateway.exceptions import ValidationError


@pytest.fixture
def validator():
    return RecordValidator()


def test_validate_a_record(validator):
    record = RecordModel(type=RecordType.A, name="test", value="192.168.1.1", ttl=3600)
    assert validator.validate_record(record) is True


def test_validate_invalid_a_record(validator):
    record = RecordModel(type=RecordType.A, name="test", value="invalid.ip", ttl=3600)
    with pytest.raises(ValidationError):
        validator.validate_record(record)


def test_validate_aaaa_record(validator):
    record = RecordModel(
        type=RecordType.AAAA, name="test", value="2001:db8::1", ttl=3600
    )
    assert validator.validate_record(record) is True


def test_validate_invalid_aaaa_record(validator):
    record = RecordModel(
        type=RecordType.AAAA, name="test", value="192.168.1.1", ttl=3600
    )
    with pytest.raises(ValidationError):
        validator.validate_record(record)


def test_validate_cname_record(validator):
    record = RecordModel(
        type=RecordType.CNAME, name="www", value="example.com.", ttl=3600
    )
    assert validator.validate_record(record) is True


def test_validate_invalid_cname_record(validator):
    record = RecordModel(type=RecordType.CNAME, name="@", value="example.com", ttl=3600)
    with pytest.raises(ValidationError):
        validator.validate_record(record)


def test_validate_mx_record(validator):
    record = RecordModel(
        type=RecordType.MX, name="@", value="mail.example.com.", priority=10, ttl=3600
    )
    assert validator.validate_record(record) is True


def test_validate_invalid_mx_record(validator):
    record = RecordModel(
        type=RecordType.MX, name="@", value="mail.example.com.", priority=-1, ttl=3600
    )
    with pytest.raises(ValidationError):
        validator.validate_record(record)


def test_validate_txt_record(validator):
    record = RecordModel(
        type=RecordType.TXT,
        name="@",
        value="v=spf1 include:_spf.example.com ~all",
        ttl=3600,
    )
    assert validator.validate_record(record) is True


def test_validate_srv_record(validator):
    record = RecordModel(
        type=RecordType.SRV,
        name="_sip._tcp",
        value="sip.example.com.",
        priority=10,
        weight=20,
        port=5060,
        ttl=3600,
    )
    assert validator.validate_record(record) is True


def test_validate_invalid_srv_record(validator):
    record = RecordModel(
        type=RecordType.SRV,
        name="invalid",
        value="sip.example.com.",
        priority=10,
        weight=20,
        port=5060,
        ttl=3600,
    )
    with pytest.raises(ValidationError):
        validator.validate_record(record)


def test_validate_ptr_record(validator):
    record = RecordModel(
        type=RecordType.PTR,
        name="1.1.168.192.in-addr.arpa",
        value="host.example.com.",
        ttl=3600,
    )
    assert validator.validate_record(record) is True


def test_validate_invalid_ptr_record(validator):
    record = RecordModel(
        type=RecordType.PTR, name="invalid", value="host.example.com", ttl=3600
    )
    with pytest.raises(ValidationError):
        validator.validate_record(record)


def test_validate_caa_record(validator):
    record = RecordModel(
        type=RecordType.CAA, name="@", value='0 issue "letsencrypt.org"', ttl=3600
    )
    assert validator.validate_record(record) is True


def test_validate_invalid_caa_record(validator):
    record = RecordModel(type=RecordType.CAA, name="@", value="invalid", ttl=3600)
    with pytest.raises(ValidationError):
        validator.validate_record(record)


def test_validate_ns_record(validator):
    record = RecordModel(
        type=RecordType.NS, name="@", value="ns1.example.com.", ttl=3600
    )
    assert validator.validate_record(record) is True


def test_validate_invalid_ns_record(validator):
    record = RecordModel(type=RecordType.NS, name="@", value="", ttl=3600)
    with pytest.raises(ValidationError):
        validator.validate_record(record)


def test_validate_soa_record(validator):
    record = RecordModel(
        type=RecordType.SOA,
        name="@",
        value="ns1.example.com. hostmaster.example.com. 2023010101 3600 600 604800 300",
        ttl=3600,
    )
    assert validator.validate_record(record) is True


def test_validate_invalid_soa_record(validator):
    record = RecordModel(type=RecordType.SOA, name="@", value="invalid", ttl=3600)
    with pytest.raises(ValidationError):
        validator.validate_record(record)
