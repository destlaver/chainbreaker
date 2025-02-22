#!/usr/bin/python

# Author : n0fate
# E-Mail rapfer@gmail.com, n0fate@n0fate.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

import argparse
import os
from sys import exit
import struct
from binascii import unhexlify
import datetime
from hexdump import hexdump

from pbkdf2 import pbkdf2

from pyDes import triple_des, CBC
from ctypes import *
from Schema import *

from validator import Validator

ATOM_SIZE = 4
SIZEOFKEYCHAINTIME = 16

KEYCHAIN_SIGNATURE = "kych"

BLOCKSIZE = 8
KEYLEN = 24


class _APPL_DB_HEADER(BigEndianStructure):
    _fields_ = [
        ("Signature", c_char * 4),
        ("Version", c_int),
        ("HeaderSize", c_int),
        ("SchemaOffset", c_int),
        ("AuthOffset", c_int)
    ]


class _APPL_DB_SCHEMA(BigEndianStructure):
    _fields_ = [
        ("SchemaSize", c_int),
        ("TableCount", c_int)
    ]


class _KEY_BLOB_REC_HEADER(BigEndianStructure):
    _fields_ = [
        ("RecordSize", c_uint),
        ("RecordCount", c_uint),
        ("Dummy", c_char * 0x7C),
    ]


class _GENERIC_PW_HEADER(BigEndianStructure):
    _fields_ = [
        ("RecordSize", c_uint),
        ("RecordNumber", c_uint),
        ("Unknown2", c_uint),
        ("Unknown3", c_uint),
        ("SSGPArea", c_uint),
        ("Unknown5", c_uint),
        ("CreationDate", c_uint),
        ("ModDate", c_uint),
        ("Description", c_uint),
        ("Comment", c_uint),
        ("Creator", c_uint),
        ("Type", c_uint),
        ("ScriptCode", c_uint),
        ("PrintName", c_uint),
        ("Alias", c_uint),
        ("Invisible", c_uint),
        ("Negative", c_uint),
        ("CustomIcon", c_uint),
        ("Protected", c_uint),
        ("Account", c_uint),
        ("Service", c_uint),
        ("Generic", c_uint)
    ]


class _APPLE_SHARE_HEADER(BigEndianStructure):
    _fields_ = [
        ("RecordSize", c_uint),
        ("RecordNumber", c_uint),
        ("Unknown2", c_uint),
        ("Unknown3", c_uint),
        ("SSGPArea", c_uint),
        ("Unknown5", c_uint),
        ("CreationDate", c_uint),
        ("ModDate", c_uint),
        ("Description", c_uint),
        ("Comment", c_uint),
        ("Creator", c_uint),
        ("Type", c_uint),
        ("ScriptCode", c_uint),
        ("PrintName", c_uint),
        ("Alias", c_uint),
        ("Invisible", c_uint),
        ("Negative", c_uint),
        ("CustomIcon", c_uint),
        ("Protected", c_uint),
        ("Account", c_uint),
        ("Volume", c_uint),
        ("Server", c_uint),
        ("Protocol", c_uint),
        ("AuthType", c_uint),
        ("Address", c_uint),
        ("Signature", c_uint)
    ]


class _INTERNET_PW_HEADER(BigEndianStructure):
    _fields_ = [
        ("RecordSize", c_uint),
        ("RecordNumber", c_uint),
        ("Unknown2", c_uint),
        ("Unknown3", c_uint),
        ("SSGPArea", c_uint),
        ("Unknown5", c_uint),
        ("CreationDate", c_uint),
        ("ModDate", c_uint),
        ("Description", c_uint),
        ("Comment", c_uint),
        ("Creator", c_uint),
        ("Type", c_uint),
        ("ScriptCode", c_uint),
        ("PrintName", c_uint),
        ("Alias", c_uint),
        ("Invisible", c_uint),
        ("Negative", c_uint),
        ("CustomIcon", c_uint),
        ("Protected", c_uint),
        ("Account", c_uint),
        ("SecurityDomain", c_uint),
        ("Server", c_uint),
        ("Protocol", c_uint),
        ("AuthType", c_uint),
        ("Port", c_uint),
        ("Path", c_uint)
    ]


class _X509_CERT_HEADER(BigEndianStructure):
    _fields_ = [
        ("RecordSize", c_uint),
        ("RecordNumber", c_uint),
        ("Unknown1", c_uint),
        ("Unknown2", c_uint),
        ("CertSize", c_uint),
        ("Unknown3", c_uint),
        ("CertType", c_uint),
        ("CertEncoding", c_uint),
        ("PrintName", c_uint),
        ("Alias", c_uint),
        ("Subject", c_uint),
        ("Issuer", c_uint),
        ("SerialNumber", c_uint),
        ("SubjectKeyIdentifier", c_uint),
        ("PublicKeyHash", c_uint)
    ]


# http://www.opensource.apple.com/source/Security/Security-55179.1/include/security_cdsa_utilities/KeySchema.h
# http://www.opensource.apple.com/source/libsecurity_keychain/libsecurity_keychain-36940/lib/SecKey.h
class _SECKEY_HEADER(BigEndianStructure):
    _fields_ = [
        ("RecordSize", c_uint32),
        ("RecordNumber", c_uint32),
        ("Unknown1", c_uint32),
        ("Unknown2", c_uint32),
        ("BlobSize", c_uint32),
        ("Unknown3", c_uint32),
        ("KeyClass", c_uint32),
        ("PrintName", c_uint32),
        ("Alias", c_uint32),
        ("Permanent", c_uint32),
        ("Private", c_uint32),
        ("Modifiable", c_uint32),
        ("Label", c_uint32),
        ("ApplicationTag", c_uint32),
        ("KeyCreator", c_uint32),
        ("KeyType", c_uint32),
        ("KeySizeInBits", c_uint32),
        ("EffectiveKeySize", c_uint32),
        ("StartDate", c_uint32),
        ("EndDate", c_uint32),
        ("Sensitive", c_uint32),
        ("AlwaysSensitive", c_uint32),
        ("Extractable", c_uint32),
        ("NeverExtractable", c_uint32),
        ("Encrypt", c_uint32),
        ("Decrypt", c_uint32),
        ("Derive", c_uint32),
        ("Sign", c_uint32),
        ("Verify", c_uint32),
        ("SignRecover", c_uint32),
        ("VerifyRecover", c_uint32),
        ("Wrap", c_uint32),
        ("UnWrap", c_uint32)
    ]


class _TABLE_HEADER(BigEndianStructure):
    _fields_ = [
        ("TableSize", c_uint),
        ("TableId", c_uint),
        ("RecordCount", c_uint),
        ("Records", c_uint),
        ("IndexesOffset", c_uint),
        ("FreeListHead", c_uint),
        ("RecordNumbersCount", c_uint),
    ]


"""
class _SCHEMA_INFO_RECORD(BigEndianStructure):
    _fields_ = [
        ("RecordSize", c_uint),
        ("RecordNumber", c_uint),
        ("Unknown2", c_uint),
        ("Unknown3", c_uint),
        ("Unknown4", c_uint),
        ("Unknown5", c_uint),
        ("Unknown6", c_uint),
        ("RecordType", c_uint),
        ("DataSize", c_uint),
        ("Data", c_uint)
    ]
"""


class _COMMON_BLOB(BigEndianStructure):
    _fields_ = [
        ("magic", c_uint32),
        ("blobVersion", c_uint32)
    ]


# _ENCRYPTED_BLOB_METADATA
class _KEY_BLOB(BigEndianStructure):
    _fields_ = [
        ("CommonBlob", _COMMON_BLOB),
        ("startCryptoBlob", c_uint32),
        ("totalLength", c_uint32),
        ("iv", c_ubyte * 8)
    ]


class _DB_PARAMETERS(BigEndianStructure):
    _fields_ = [
        ("idleTimeout", c_uint32),  # uint32
        ("lockOnSleep", c_uint32)  # uint8
    ]


class _DB_BLOB(BigEndianStructure):
    _fields_ = [
        ("CommonBlob", _COMMON_BLOB),
        ("startCryptoBlob", c_uint32),
        ("totalLength", c_uint32),
        ("randomSignature", c_ubyte * 16),
        ("sequence", c_uint32),
        ("params", _DB_PARAMETERS),
        ("salt", c_ubyte * 20),
        ("iv", c_ubyte * 8),
        ("blobSignature", c_ubyte * 20)
    ]


class _SSGP(BigEndianStructure):
    _fields_ = [
        ("magic", c_char * 4),
        ("label", c_ubyte * 16),
        ("iv", c_ubyte * 8)
    ]

# /var/db/SystemKey contains the master key for /Library/Keychains/System.keychain
class _UNLOCK_BLOB(BigEndianStructure):
    _fields_ = [
        ("CommonBlob", _COMMON_BLOB),
        ("masterKey", c_char*24),
        ("blobSignature", c_ubyte * 16)
    ]

def _memcpy(buf, fmt):
    return cast(c_char_p(buf), POINTER(fmt)).contents


class KeyChain():
    def __init__(self, filepath):
        self.filepath = filepath
        self.fbuf = ''

    def open(self):
        try:
            fhandle = open(self.filepath, 'rb')
        except:
            return False
        self.fbuf = fhandle.read()
        if len(self.fbuf):
            fhandle.close()
            return True
        return False

    def checkValidKeychain(self):
        if self.fbuf[0:4] != KEYCHAIN_SIGNATURE:
            return False
        return True

    ## get apple DB Header
    def getHeader(self):
        header = _memcpy(self.fbuf[:sizeof(_APPL_DB_HEADER)], _APPL_DB_HEADER)

        return header

    def getSchemaInfo(self, offset):
        table_list = []
        # schema_info = struct.unpack(APPL_DB_SCHEMA, self.fbuf[offset:offset + APPL_DB_SCHEMA_SIZE])
        _schemainfo = _memcpy(self.fbuf[offset:offset + sizeof(_APPL_DB_SCHEMA)], _APPL_DB_SCHEMA)
        for i in xrange(_schemainfo.TableCount):
            BASE_ADDR = sizeof(_APPL_DB_HEADER) + sizeof(_APPL_DB_SCHEMA)
            table_list.append(
                struct.unpack('>I', self.fbuf[BASE_ADDR + (ATOM_SIZE * i):BASE_ADDR + (ATOM_SIZE * i) + ATOM_SIZE])[0])

        return _schemainfo, table_list

    def getTable(self, offset):
        record_list = []
        BASE_ADDR = sizeof(_APPL_DB_HEADER) + offset

        TableMetaData = _memcpy(self.fbuf[BASE_ADDR:BASE_ADDR + sizeof(_TABLE_HEADER)], _TABLE_HEADER)

        RECORD_OFFSET_BASE = BASE_ADDR + sizeof(_TABLE_HEADER)

        record_count = 0
        offset = 0
        while TableMetaData.RecordCount != record_count:
            RecordOffset = struct.unpack('>I', self.fbuf[
                                               RECORD_OFFSET_BASE + (ATOM_SIZE * offset):RECORD_OFFSET_BASE + (
                                                       ATOM_SIZE * offset) + ATOM_SIZE])[0]
            # if len(record_list) >= 1:
            #     if record_list[len(record_list)-1] >= RecordOffset:
            #         continue
            if (RecordOffset != 0x00) and (RecordOffset % 4 == 0):
                record_list.append(RecordOffset)
                # print ' [-] Record Offset: 0x%.8x'%RecordOffset
                record_count += 1
            offset += 1

        return TableMetaData, record_list

    def getTablenametoList(self, recordList, tableList):
        TableDic = {}
        for count in xrange(len(recordList)):
            tableMeta, GenericList = self.getTable(tableList[count])
            TableDic[tableMeta.TableId] = count  # extract valid table list

        return len(recordList), TableDic

    def getKeyblobRecord(self, base_addr, offset):

        BASE_ADDR = sizeof(_APPL_DB_HEADER) + base_addr + offset

        KeyBlobRecHeader = _memcpy(self.fbuf[BASE_ADDR:BASE_ADDR + sizeof(_KEY_BLOB_REC_HEADER)], _KEY_BLOB_REC_HEADER)

        record = self.fbuf[
                 BASE_ADDR + sizeof(_KEY_BLOB_REC_HEADER):BASE_ADDR + KeyBlobRecHeader.RecordSize]  # password data area

        KeyBlobRecord = _memcpy(record[:+sizeof(_KEY_BLOB)], _KEY_BLOB)
        # hexdump(KeyBlobRecord.iv)

        if SECURE_STORAGE_GROUP != str(record[KeyBlobRecord.totalLength + 8:KeyBlobRecord.totalLength + 8 + 4]):
            return '', '', '', 1

        CipherLen = KeyBlobRecord.totalLength - KeyBlobRecord.startCryptoBlob
        if CipherLen % BLOCKSIZE != 0:
            print "Bad ciphertext len"
            return '', '', '', 1

        ciphertext = record[KeyBlobRecord.startCryptoBlob:KeyBlobRecord.totalLength]

        # match data, keyblob_ciphertext, Initial Vector, success
        return record[KeyBlobRecord.totalLength + 8:KeyBlobRecord.totalLength + 8 + 20], ciphertext, KeyBlobRecord.iv, 0

    def getGenericPWRecord(self, base_addr, offset):
        record = []

        BASE_ADDR = sizeof(_APPL_DB_HEADER) + base_addr + offset

        RecordMeta = _memcpy(self.fbuf[BASE_ADDR:BASE_ADDR + sizeof(_GENERIC_PW_HEADER)], _GENERIC_PW_HEADER)

        Buffer = self.fbuf[BASE_ADDR + sizeof(
            _GENERIC_PW_HEADER):BASE_ADDR + RecordMeta.RecordSize]  # record_meta[0] => record size

        if RecordMeta.SSGPArea != 0:
            record.append(Buffer[:RecordMeta.SSGPArea])
        else:
            record.append('')

        record.append(self.getKeychainTime(BASE_ADDR, RecordMeta.CreationDate & 0xFFFFFFFE))
        record.append(self.getKeychainTime(BASE_ADDR, RecordMeta.ModDate & 0xFFFFFFFE))

        record.append(self.getLV(BASE_ADDR, RecordMeta.Description & 0xFFFFFFFE))

        record.append(self.getFourCharCode(BASE_ADDR, RecordMeta.Creator & 0xFFFFFFFE))
        record.append(self.getFourCharCode(BASE_ADDR, RecordMeta.Type & 0xFFFFFFFE))

        record.append(self.getLV(BASE_ADDR, RecordMeta.PrintName & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.Alias & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.Account & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.Service & 0xFFFFFFFE))

        return record

    def getInternetPWRecord(self, base_addr, offset):
        record = []

        BASE_ADDR = sizeof(_APPL_DB_HEADER) + base_addr + offset

        RecordMeta = _memcpy(self.fbuf[BASE_ADDR:BASE_ADDR + sizeof(_INTERNET_PW_HEADER)], _INTERNET_PW_HEADER)

        Buffer = self.fbuf[BASE_ADDR + sizeof(_INTERNET_PW_HEADER):BASE_ADDR + RecordMeta.RecordSize]

        if RecordMeta.SSGPArea != 0:
            record.append(Buffer[:RecordMeta.SSGPArea])
        else:
            record.append('')

        record.append(self.getKeychainTime(BASE_ADDR, RecordMeta.CreationDate & 0xFFFFFFFE))
        record.append(self.getKeychainTime(BASE_ADDR, RecordMeta.ModDate & 0xFFFFFFFE))

        record.append(self.getLV(BASE_ADDR, RecordMeta.Description & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.Comment & 0xFFFFFFFE))

        record.append(self.getFourCharCode(BASE_ADDR, RecordMeta.Creator & 0xFFFFFFFE))
        record.append(self.getFourCharCode(BASE_ADDR, RecordMeta.Type & 0xFFFFFFFE))

        record.append(self.getLV(BASE_ADDR, RecordMeta.PrintName & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.Alias & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.Protected & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.Account & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.SecurityDomain & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.Server & 0xFFFFFFFE))

        record.append(self.getFourCharCode(BASE_ADDR, RecordMeta.Protocol & 0xFFFFFFFE))

        record.append(self.getLV(BASE_ADDR, RecordMeta.AuthType & 0xFFFFFFFE))

        record.append(self.getInt(BASE_ADDR, RecordMeta.Port & 0xFFFFFFFE))

        record.append(self.getLV(BASE_ADDR, RecordMeta.Path & 0xFFFFFFFE))

        return record

    def getx509Record(self, base_addr, offset):
        record = []

        BASE_ADDR = sizeof(_APPL_DB_HEADER) + base_addr + offset

        RecordMeta = _memcpy(self.fbuf[BASE_ADDR:BASE_ADDR + sizeof(_X509_CERT_HEADER)], _X509_CERT_HEADER)

        x509Certificate = self.fbuf[BASE_ADDR + sizeof(_X509_CERT_HEADER):BASE_ADDR + sizeof(
            _X509_CERT_HEADER) + RecordMeta.CertSize]

        record.append(self.getInt(BASE_ADDR, RecordMeta.CertType & 0xFFFFFFFE))  # Cert Type
        record.append(self.getInt(BASE_ADDR, RecordMeta.CertEncoding & 0xFFFFFFFE))  # Cert Encoding

        record.append(self.getLV(BASE_ADDR, RecordMeta.PrintName & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.Alias & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.Subject & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.Issuer & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.SerialNumber & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.SubjectKeyIdentifier & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.PublicKeyHash & 0xFFFFFFFE))

        record.append(x509Certificate)
        return record

    def getKeyRecord(self, base_addr, offset):  ## PUBLIC and PRIVATE KEY
        record = []

        BASE_ADDR = sizeof(_APPL_DB_HEADER) + base_addr + offset

        RecordMeta = _memcpy(self.fbuf[BASE_ADDR:BASE_ADDR + sizeof(_SECKEY_HEADER)], _SECKEY_HEADER)

        KeyBlob = self.fbuf[BASE_ADDR + sizeof(_SECKEY_HEADER):BASE_ADDR + sizeof(_SECKEY_HEADER) + RecordMeta.BlobSize]

        record.append(self.getLV(BASE_ADDR, RecordMeta.PrintName & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.Label & 0xFFFFFFFE))
        record.append(self.getInt(BASE_ADDR, RecordMeta.KeyClass & 0xFFFFFFFE))
        record.append(self.getInt(BASE_ADDR, RecordMeta.Private & 0xFFFFFFFE))
        record.append(self.getInt(BASE_ADDR, RecordMeta.KeyType & 0xFFFFFFFE))
        record.append(self.getInt(BASE_ADDR, RecordMeta.KeySizeInBits & 0xFFFFFFFE))
        record.append(self.getInt(BASE_ADDR, RecordMeta.EffectiveKeySize & 0xFFFFFFFE))
        record.append(self.getInt(BASE_ADDR, RecordMeta.Extractable & 0xFFFFFFFE))
        record.append(str(self.getLV(BASE_ADDR, RecordMeta.KeyCreator & 0xFFFFFFFE)).split('\x00')[0])

        IV, Key = self.getEncryptedDatainBlob(KeyBlob)
        record.append(IV)
        record.append(Key)

        return record

    def getEncryptedDatainBlob(self, BlobBuf):
        KeyBlob = _memcpy(BlobBuf[:sizeof(_KEY_BLOB)], _KEY_BLOB)

        if KeyBlob.CommonBlob.magic != 0xFADE0711:
            return '', ''

        KeyData = BlobBuf[KeyBlob.startCryptoBlob:KeyBlob.totalLength]
        return KeyBlob.iv, KeyData  # IV, Encrypted Data

    def getKeychainTime(self, BASE_ADDR, pCol):
        if pCol <= 0:
            return ''
        else:
            data = str(struct.unpack('>16s', self.fbuf[BASE_ADDR + pCol:BASE_ADDR + pCol + struct.calcsize('>16s')])[0])
            return datetime.datetime.strptime(data.strip('\x00'), '%Y%m%d%H%M%SZ')

    def getInt(self, BASE_ADDR, pCol):
        if pCol <= 0:
            return 0
        else:
            return struct.unpack('>I', self.fbuf[BASE_ADDR + pCol:BASE_ADDR + pCol + 4])[0]

    def getFourCharCode(self, BASE_ADDR, pCol):
        if pCol <= 0:
            return ''
        else:
            return struct.unpack('>4s', self.fbuf[BASE_ADDR + pCol:BASE_ADDR + pCol + 4])[0]

    def getLV(self, BASE_ADDR, pCol):
        if pCol <= 0:
            return ''

        str_length = struct.unpack('>I', self.fbuf[BASE_ADDR + pCol:BASE_ADDR + pCol + 4])[0]
        # 4byte arrangement
        if (str_length % 4) == 0:
            real_str_len = (str_length / 4) * 4
        else:
            real_str_len = ((str_length / 4) + 1) * 4
        unpack_value = '>' + str(real_str_len) + 's'
        try:
            data = struct.unpack(unpack_value, self.fbuf[BASE_ADDR + pCol + 4:BASE_ADDR + pCol + 4 + real_str_len])[0]
        except struct.error:
            # print 'Length is too long : %d'%real_str_len
            return ''
        return data

    def getAppleshareRecord(self, base_addr, offset):
        record = []

        BASE_ADDR = sizeof(_APPL_DB_HEADER) + base_addr + offset

        RecordMeta = _memcpy(self.fbuf[BASE_ADDR:BASE_ADDR + sizeof(_APPLE_SHARE_HEADER)], _APPLE_SHARE_HEADER)

        Buffer = self.fbuf[BASE_ADDR + sizeof(_APPLE_SHARE_HEADER):BASE_ADDR + RecordMeta.RecordSize]

        if RecordMeta.SSGPArea != 0:
            record.append(Buffer[:RecordMeta.SSGPArea])
        else:
            record.append('')

        record.append(self.getKeychainTime(BASE_ADDR, RecordMeta.CreationDate & 0xFFFFFFFE))
        record.append(self.getKeychainTime(BASE_ADDR, RecordMeta.ModDate & 0xFFFFFFFE))

        record.append(self.getLV(BASE_ADDR, RecordMeta.Description & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.Comment & 0xFFFFFFFE))

        record.append(self.getFourCharCode(BASE_ADDR, RecordMeta.Creator & 0xFFFFFFFE))
        record.append(self.getFourCharCode(BASE_ADDR, RecordMeta.Type & 0xFFFFFFFE))

        record.append(self.getLV(BASE_ADDR, RecordMeta.PrintName & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.Alias & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.Protected & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.Account & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.Volume & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.Server & 0xFFFFFFFE))

        record.append(self.getFourCharCode(BASE_ADDR, RecordMeta.Protocol & 0xFFFFFFFE))

        record.append(self.getLV(BASE_ADDR, RecordMeta.Address & 0xFFFFFFFE))
        record.append(self.getLV(BASE_ADDR, RecordMeta.Signature & 0xFFFFFFFE))

        return record

    ## decrypted dbblob area
    ## Documents : http://www.opensource.apple.com/source/securityd/securityd-55137.1/doc/BLOBFORMAT
    ## http://www.opensource.apple.com/source/libsecurity_keychain/libsecurity_keychain-36620/lib/StorageManager.cpp
    def SSGPDecryption(self, ssgp, dbkey):
        SSGP = _memcpy(ssgp, _SSGP)
        plain = kcdecrypt(dbkey, SSGP.iv, ssgp[sizeof(_SSGP):])

        return plain

    # Documents : http://www.opensource.apple.com/source/securityd/securityd-55137.1/doc/BLOBFORMAT
    # source : http://www.opensource.apple.com/source/libsecurity_cdsa_client/libsecurity_cdsa_client-36213/lib/securestorage.cpp
    # magicCmsIV : http://www.opensource.apple.com/source/Security/Security-28/AppleCSP/AppleCSP/wrapKeyCms.cpp
    def KeyblobDecryption(self, encryptedblob, iv, dbkey):

        magicCmsIV = unhexlify('4adda22c79e82105')
        plain = kcdecrypt(dbkey, magicCmsIV, encryptedblob)

        if plain.__len__() == 0:
            return ''

        # now we handle the unwrapping. we need to take the first 32 bytes,
        # and reverse them.
        revplain = ''
        for i in range(32):
            revplain += plain[31 - i]

        # now the real key gets found. */
        plain = kcdecrypt(dbkey, iv, revplain)

        keyblob = plain[4:]

        if len(keyblob) != KEYLEN:
            # raise "Bad decrypted keylen!"
            return ''

        return keyblob

    # test code
    # http://opensource.apple.com/source/libsecurity_keychain/libsecurity_keychain-55044/lib/KeyItem.cpp
    def PrivateKeyDecryption(self, encryptedblob, iv, dbkey):
        magicCmsIV = unhexlify('4adda22c79e82105')
        plain = kcdecrypt(dbkey, magicCmsIV, encryptedblob)

        if plain.__len__() == 0:
            return '', ''

        # now we handle the unwrapping. we need to take the first 32 bytes,
        # and reverse them.
        revplain = ''
        for i in range(len(plain)):
            revplain += plain[len(plain) - 1 - i]

        # now the real key gets found. */
        plain = kcdecrypt(dbkey, iv, revplain)

        Keyname = plain[:12]  # Copied Buffer when user click on right and copy a key on Keychain Access
        keyblob = plain[12:]

        return Keyname, keyblob

    ## Documents : http://www.opensource.apple.com/source/securityd/securityd-55137.1/doc/BLOBFORMAT
    def generateMasterKey(self, pw, symmetrickey_offset):

        base_addr = sizeof(_APPL_DB_HEADER) + symmetrickey_offset + 0x38  # header
        dbblob = _memcpy(self.fbuf[base_addr:base_addr + sizeof(_DB_BLOB)], _DB_BLOB)

        masterkey = pbkdf2(pw, str(bytearray(dbblob.salt)), 1000, KEYLEN)
        return masterkey

    ## find DBBlob and extract Wrapping key
    def findWrappingKey(self, master, symmetrickey_offset):

        base_addr = sizeof(_APPL_DB_HEADER) + symmetrickey_offset + 0x38

        dbblob = _memcpy(self.fbuf[base_addr:base_addr + sizeof(_DB_BLOB)], _DB_BLOB)

        # get cipher text area
        ciphertext = self.fbuf[base_addr + dbblob.startCryptoBlob:base_addr + dbblob.totalLength]

        # decrypt the key
        plain = kcdecrypt(master, dbblob.iv, ciphertext)

        if plain.__len__() < KEYLEN:
            return ''

        dbkey = plain[:KEYLEN]

        # return encrypted wrapping key
        return dbkey


# SOURCE : extractkeychain.py
def kcdecrypt(key, iv, data):
    if len(data) == 0:
        # print>>stderr, "FileSize is 0"
        return ''

    if len(data) % BLOCKSIZE != 0:
        return ''


    cipher = triple_des(key, CBC, str(bytearray(iv)))

    # the line below is for pycrypto instead
    # cipher = DES3.new( key, DES3.MODE_CBC, iv )

    plain = cipher.decrypt(data)

    # now check padding
    pad = ord(plain[-1])
    if pad > 8:
        # print>> stderr, "Bad padding byte. You probably have a wrong password"
        return ''


    for z in plain[-pad:]:
        if ord(z) != pad:
            # print>> stderr, "Bad padding. You probably have a wrong password"
            return ''

    plain = plain[:-pad]

    return plain


BASEPATH = os.getcwd() + '/exported/'

if not os.path.exists(BASEPATH):
    os.makedirs(BASEPATH)


def add_file(directory, filename='default', key=None, cert=None):
    # print 'into function key={}, cert={}'.format(key, cert)
    target_path = BASEPATH + directory
    if not os.path.exists(target_path):
        os.makedirs(target_path)
    if key is not None:
        with open(target_path + '/{}.key'.format(filename), 'w+') as f:
            f.write(key)
    if cert is not None:
        with open(target_path + '/{}.crt'.format(filename), 'w+') as f:
            f.write(cert)


def main():
    parser = argparse.ArgumentParser(description='Tool for OS X Keychain Analysis by @n0fate')
    parser.add_argument('-f', '--file', nargs=1, help='Keychain file(*.keychain)', required=True)
    # parser.add_argument('-x', '--exportfile', nargs=1, help='Export a filename (SQLite, optional)', required=False)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-k', '--key', nargs=1, help='Keychain Masterkey', required=False)
    group.add_argument('-u', '--unlockfile', nargs=1, help='System.keychain unlock file (/var/db/SystemKey)', required=False)
    group.add_argument('-p', '--password', nargs=1, help='Keychain Password', required=False)
    args = parser.parse_args()

    if os.path.exists(args.file[0]) is False:
        print '[!] ERROR: Keychain is not exists'
        parser.print_help()
        exit()

    keychain = KeyChain(args.file[0])

    if keychain.open() is False:
        print '[!] ERROR: %s Open Failed' % args.file[0]
        parser.print_help()
        exit()

    KeychainHeader = keychain.getHeader()

    if KeychainHeader.Signature != KEYCHAIN_SIGNATURE:
        print '[!] ERROR: Invalid Keychain Format'
        parser.print_help()
        exit()

    SchemaInfo, TableList = keychain.getSchemaInfo(KeychainHeader.SchemaOffset)

    TableMetadata, RecordList = keychain.getTable(TableList[0])

    tableCount, tableEnum = keychain.getTablenametoList(RecordList, TableList)

    # generate database key
    if args.password is not None:
        masterkey = keychain.generateMasterKey(args.password[0], TableList[tableEnum[CSSM_DL_DB_RECORD_METADATA]])
        dbkey = keychain.findWrappingKey(masterkey, TableList[tableEnum[CSSM_DL_DB_RECORD_METADATA]])

    elif args.key is not None:
        dbkey = keychain.findWrappingKey(unhexlify(args.key[0]), TableList[tableEnum[CSSM_DL_DB_RECORD_METADATA]])

    elif args.unlockfile is not None:
        with open(args.unlockfile[0], mode='rb') as uf:
            filecontent = uf.read()
        unlockkeyblob = _memcpy(filecontent, _UNLOCK_BLOB)
        dbkey = keychain.findWrappingKey(unlockkeyblob.masterKey, TableList[tableEnum[CSSM_DL_DB_RECORD_METADATA]])
    else:
        print '[!] ERROR: password or master key candidate is invalid'
        exit()

    if len(dbkey) == 0:
        print '[!] ERROR: password or master key candidate is invalid'
        exit()

    # DEBUG
    print ' [-] DB Key'
    # hexdump(dbkey)

    key_list = {}  # keyblob list

    # get symmetric key blob
    print '[+] Symmetric Key Table:'
    # print '0x%.8x' % (
    #             sizeof(_APPL_DB_HEADER) + TableList[tableEnum[CSSM_DL_DB_RECORD_SYMMETRIC_KEY]])
    TableMetadata, symmetrickey_list = keychain.getTable(TableList[tableEnum[CSSM_DL_DB_RECORD_SYMMETRIC_KEY]])

    for symmetrickey_record in symmetrickey_list:
        keyblob, ciphertext, iv, return_value = keychain.getKeyblobRecord(
            TableList[tableEnum[CSSM_DL_DB_RECORD_SYMMETRIC_KEY]],
            symmetrickey_record)
        if return_value == 0:
            passwd = keychain.KeyblobDecryption(ciphertext, iv, dbkey)
            if passwd != '':
                key_list[keyblob] = passwd

    try:
        TableMetadata, genericpw_list = keychain.getTable(TableList[tableEnum[CSSM_DL_DB_RECORD_GENERIC_PASSWORD]])

        for genericpw in genericpw_list:
            record = keychain.getGenericPWRecord(TableList[tableEnum[CSSM_DL_DB_RECORD_GENERIC_PASSWORD]], genericpw)
            print '[+] Generic Password Record'
            try:
                real_key = key_list[record[0][0:20]]
                passwd = keychain.SSGPDecryption(record[0], real_key)
            except KeyError:
                passwd = ''
            print ' [-] Create DateTime: %s' % record[1]  # 16byte string
            print ' [-] Last Modified DateTime: %s' % record[2]  # 16byte string
            print ' [-] Description : %s' % record[3]
            print ' [-] Creator : %s' % record[4]
            print ' [-] Type : %s' % record[5]
            print ' [-] PrintName : %s' % record[6]
            print ' [-] Alias : %s' % record[7]
            print ' [-] Account : %s' % record[8]
            print ' [-] Service : %s' % record[9]
            print ' [-] Password'
            hexdump(passwd)
            print ''

    except KeyError:
        print '[!] Generic Password Table is not available'
        pass

    try:
        TableMetadata, internetpw_list = keychain.getTable(TableList[tableEnum[CSSM_DL_DB_RECORD_INTERNET_PASSWORD]])

        for internetpw in internetpw_list:
            record = keychain.getInternetPWRecord(TableList[tableEnum[CSSM_DL_DB_RECORD_INTERNET_PASSWORD]], internetpw)
            print '[+] Internet Record'
            try:
                real_key = key_list[record[0][0:20]]
                passwd = keychain.SSGPDecryption(record[0], real_key)
            except KeyError:
                passwd = ''
            print ' [-] Create DateTime: %s' % record[1]  # 16byte string
            print ' [-] Last Modified DateTime: %s' % record[2]  # 16byte string
            print ' [-] Description : %s' % record[3]
            print ' [-] Comment : %s' % record[4]
            print ' [-] Creator : %s' % record[5]
            print ' [-] Type : %s' % record[6]
            print ' [-] PrintName : %s' % record[7]
            print ' [-] Alias : %s' % record[8]
            print ' [-] Protected : %s' % record[9]
            print ' [-] Account : %s' % record[10]
            print ' [-] SecurityDomain : %s' % record[11]
            print ' [-] Server : %s' % record[12]
            try:
                print ' [-] Protocol Type : %s' % PROTOCOL_TYPE[record[13]]
            except KeyError:
                print ' [-] Protocol Type : %s' % record[13]
            try:
                print ' [-] Auth Type : %s' % AUTH_TYPE[record[14]]
            except KeyError:
                print ' [-] Auth Type : %s' % record[14]
            print ' [-] Port : %d' % record[15]
            print ' [-] Path : %s' % record[16]
            print ' [-] Password'
            hexdump(passwd)
            print ''

    except KeyError:
        print '[!] Internet Password Table is not available'
        pass

    try:
        TableMetadata, applesharepw_list = keychain.getTable(
            TableList[tableEnum[CSSM_DL_DB_RECORD_APPLESHARE_PASSWORD]])

        for applesharepw in applesharepw_list:
            record = keychain.getAppleshareRecord(TableList[tableEnum[CSSM_DL_DB_RECORD_APPLESHARE_PASSWORD]],
                                                  applesharepw)
            print '[+] AppleShare Record (no more used OS X)'
            try:
                real_key = key_list[record[0][0:20]]
                passwd = keychain.SSGPDecryption(record[0], real_key)
            except KeyError:
                passwd = ''
            # print ''
            # print ' [-] Create DateTime: %s' % record[1]  # 16byte string
            # print ' [-] Last Modified DateTime: %s' % record[2]  # 16byte string
            # print ' [-] Description : %s' % record[3]
            # print ' [-] Comment : %s' % record[4]
            # print ' [-] Creator : %s' % record[5]
            # print ' [-] Type : %s' % record[6]
            # print ' [-] PrintName : %s' % record[7]
            # print ' [-] Alias : %s' % record[8]
            # print ' [-] Protected : %s' % record[9]
            # print ' [-] Account : %s' % record[10]
            # print ' [-] Volume : %s' % record[11]
            # print ' [-] Server : %s' % record[12]
            # try:
                # print ' [-] Protocol Type : %s' % PROTOCOL_TYPE[record[13]]
            # except KeyError:
            #     print ' [-] Protocol Type : %s' % record[13]
            # print ' [-] Address : %d' % record[14]
            # print ' [-] Signature : %s' % record[15]
            # print ' [-] Password'
            # hexdump(passwd)
            # print ''

    except KeyError:
        print '[!] AppleShare Table is not available'
        pass

    try:
        TableMetadata, x509CertList = keychain.getTable(TableList[tableEnum[CSSM_DL_DB_RECORD_X509_CERTIFICATE]])

        for i, x509Cert in enumerate(x509CertList, 1):
            record = keychain.getx509Record(TableList[tableEnum[CSSM_DL_DB_RECORD_X509_CERTIFICATE]], x509Cert)
            print '[+] Certificate'
            # print ' [-] Cert Type: %s' % CERT_TYPE[record[0]]
            # print ' [-] Cert Encoding: %s' % CERT_ENCODING[record[1]]
            # print ' [-] PrintName : %s' % record[2]
            # print ' [-] Alias : %s' % record[3]
            # print ' [-] Subject'
            # hexdump(record[4])
            # print ' [-] Issuer :'
            # hexdump(record[5])
            # print ' [-] SerialNumber'
            # hexdump(record[6])
            # print ' [-] SubjectKeyIdentifier'
            # hexdump(record[7])
            # print ' [-] Public Key Hash'
            # hexdump(record[8])
            # print ' [-] Certificate'
            add_file(directory='certs', filename=str(i), cert=str(record[9]))
            # hexdump(record[9])
            # print ''

    except KeyError:
        print '[!] Certification Table is not available'
        pass

    try:
        TableMetadata, PublicKeyList = keychain.getTable(TableList[tableEnum[CSSM_DL_DB_RECORD_PUBLIC_KEY]])
        for PublicKey in PublicKeyList:
            record = keychain.getKeyRecord(TableList[tableEnum[CSSM_DL_DB_RECORD_PUBLIC_KEY]], PublicKey)
            print '[+] Public Key Record'
            # print ' [-] PrintName: %s' % record[0]
            # print ' [-] Label'
            # hexdump(record[1])
            # print ' [-] Key Class : %s' % KEY_TYPE[record[2]]
            # print ' [-] Private : %d' % record[3]
            # print ' [-] Key Type : %s' % CSSM_ALGORITHMS[record[4]]
            # print ' [-] Key Size : %d bits' % record[5]
            # print ' [-] Effective Key Size : %d bits' % record[6]
            # print ' [-] Extracted : %d' % record[7]
            # print ' [-] CSSM Type : %s' % STD_APPLE_ADDIN_MODULE[record[8]]
            # print ' [-] Public Key'
            # hexdump(record[10])
            # print ''

    except KeyError:
        print '[!] Public Key Table is not available'
        pass

    try:
        table_meta, PrivateKeyList = keychain.getTable(TableList[tableEnum[CSSM_DL_DB_RECORD_PRIVATE_KEY]])
        for i, PrivateKey in enumerate(PrivateKeyList, 1):
            record = keychain.getKeyRecord(TableList[tableEnum[CSSM_DL_DB_RECORD_PRIVATE_KEY]], PrivateKey)
            print '[+] Private Key Record'
            # print ' [-] PrintName: %s' % record[0]
            # print ' [-] Label'
            # hexdump(record[1])
            # print ' [-] Key Class : %s' % KEY_TYPE[record[2]]
            # print ' [-] Private : %d' % record[3]
            # print ' [-] Key Type : %s' % CSSM_ALGORITHMS[record[4]]
            # print ' [-] Key Size : %d bits' % record[5]
            # print ' [-] Effective Key Size : %d bits' % record[6]
            # print ' [-] Extracted : %d' % record[7]
            # print ' [-] CSSM Type : %s' % STD_APPLE_ADDIN_MODULE[record[8]]
            keyname, privatekey = keychain.PrivateKeyDecryption(record[10], record[9], dbkey)
            # print ' [-] Key Name'
            # hexdump(keyname)
            # print ' [-] Decrypted Private Key'
            add_file(directory='keys', filename=str(i), key=str(privatekey))
            # hexdump(privatekey)
            # print ''

    except KeyError:
        print '[!] Private Key Table is not available'
        pass

    v = Validator()

    certs = os.listdir(BASEPATH + '/certs')
    keys = os.listdir(BASEPATH + '/keys')

    k_path = BASEPATH + '/keys/{}'
    c_path = BASEPATH + '/certs/{}'

    for i, c in enumerate(certs, 1):
        for j, k in enumerate(keys, 1):
            if v.validate_by_filenames(key_path=k_path.format(k), cert_path=c_path.format(c)):
                try:
                    new_folder_name = len(os.listdir(BASEPATH + 'associated')) + 1
                except OSError:
                    new_folder_name = 1
                add_file('associated/{}'.format(new_folder_name), filename=str(i), cert=open(c_path.format(c)).read())
                add_file('associated/{}'.format(new_folder_name), filename=str(j), key=open(k_path.format(k)).read())


    exit()


if __name__ == "__main__":
    main()
