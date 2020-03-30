import sys

# Little Endian으로 되어 있는 16진수를 10진수로 변환
def LtoI(buf):
    val = 0
    for i in range(0, len(buf)):
        multi = 1
        for j in range(0, i):
            multi *= 256
        val += buf[i] * multi
    return val

def get_mft_offset(f):
    f.seek(0)
    buf = bytearray(f.read(0x200))

    sector_size = LtoI(buf[0xb:0xd])
    cluster_size = LtoI(buf[0xd:0xe])
    mft_offset = LtoI(buf[0x30:0x38]) * sector_size * cluster_size

    return sector_size, cluster_size, mft_offset

def attribute_parse(attr_off, sec, clu, f):
    count = 0
    tmp = '00'
    clu_size = [None] * 10
    clu_off = [None] * 10
    calc = 0
    tmp_size = [None] * 10
    tmp_offset = [None] * 10
    add_offset = 0

    attr_type = LtoI(attr_off[0x00:0x04])
    attr_size = LtoI(attr_off[0x04:0x08])

    runlist_off = LtoI(attr_off[0x20:0x22])
    runlist = attr_off[runlist_off:]

    while True:
        cal = int(tmp[0]) + int(tmp[1])
        runlist = runlist[cal:]

        if not (count == 0):
            runlist = runlist[1:]

        tmp = str('%x'%runlist[0])
        if runlist[0] == 0x00:
            break
        clu_size[count] = tmp[1]
        clu_off[count] = tmp[0]

        tmp_size[count] = LtoI(runlist[1:int(clu_size[count]) + 1])
        tmp_offset[count] = LtoI(runlist[int(clu_size[count]) + 1: int(clu_size[count])+int(clu_off[count]) + 1])
        tmp_offset[count] += add_offset
        add_offset = 0
        add_offset += tmp_offset[count]

        count += 1

    size = []
    offset = []
    for i in range(0, 10):
        if not (tmp_size[i] == None):
            size.append(tmp_size[i] * sec * clu)
        if not (tmp_offset[i] == None):
            offset.append(tmp_offset[i] * sec * clu)

    o = open('ouput.txt', 'wb')

    for i in range(0, len(size)):
        f.seek(offset[i])
        buf = bytearray(f.read(size[i]))
        try:
            o.write(buf)
            print("cluster run {0} : success", i)
        except Exception as e:
            print('Error : ', e)

    f.close()
    o.close()


def find_attribute(attr_off, type, sec, clu, f):
    while True:
        attr_type = LtoI(attr_off[0x00:0x04])
        if attr_type == 0x0000 or attr_type == 0xFFFF: break # NULL or EndMarker
        if attr_type == type:
            try:
                attribute_parse(attr_off, sec, clu, f)
                sys.exit(0)
            except Exception as e:
                print("Error : ", e)
        attr_size = LtoI(attr_off[0x04:0x08])
        attr_off = attr_off[attr_size:]


if __name__ == '__main__':
    # c드라이브를 파일 열기와 동일하게 연다.
    f = open('\\\\.\\c:', 'rb')
    sector_size, cluster_size, mft_offset = get_mft_offset(f)

    print(mft_offset)
    """
    f.seek(mft_offset)
    mft_buf = bytearray(f.read(0x200))
    mft_attribute_offset = LtoI(mft_buf[0x14:0x16])
    mft_size = LtoI(mft_buf[0x18:0x1c])
    attr_off = mft_buf[mft_attribute_offset:mft_size]

    find_attribute(attr_off, 0x80, sector_size, cluster_size, f)
    """
