#!/usr/bin/env python3
"""
convert van-dyk in html format to TEI

the original source text is in rtf. Before running:
 - rtf exported to html
 - manually check parallel language fragments are separated by a tab
"""
import argparse
from lxml import etree
from pysuca.utils import (
    make_xml_id,
    parse_tei,
    write_tei,
)




def strip_newlines(t):
    return t.replace('\n', ' ').replace('\t', '')


def populate_front(div, FRONT, titleStmt):
    titlePage = etree.SubElement(FRONT, "titlePage")
    docTitle = etree.SubElement(titlePage, "docTitle")
    for subdiv in div:
        _class = subdiv.attrib["class"]
        if _class == "title":
            mainTitle = etree.SubElement(docTitle, "titlePart")
            mainTitle.attrib["type"] = "main"
            t = []
            for p in subdiv:
                for span in p:
                    if span.text is not None:
                        t.append(span.text.strip())
                    elif len(span) > 0:
                        for child in span:
                            print("~~", etree.tostring(child).decode())
                            t.append(etree.tostring(child).decode())
            T = strip_newlines(' '.join(t))
            mainTitle.text = T
            title = etree.SubElement(titleStmt, "title")
            title.text = T
            title.attrib["lang"] = "nld"
        elif _class == "subtitle":
            subTitle = etree.SubElement(docTitle, "titlePart")
            subTitle.attrib["type"] = "subTitle"
            t = []
            for p in subdiv:
                for span in p:
                    if span.text is not None:
                        t.append(span.text.strip())
                    elif len(span) > 0:
                        for child in span:
                            t.append(etree.tostring(child).decode())
            T = strip_newlines(' '.join(t))
            subTitle.text = T
        elif _class == "author":
            docAuthor = etree.SubElement(titlePage, "docAuthor")
            A = ""
            for p in subdiv:
                for span in p:
                    A += span.text
            docAuthor.text = A
            author = etree.SubElement(titleStmt, "author")
            author.text = A
        elif _class == "publicationStatement":
            imprint = etree.SubElement(titlePage, "docImprint")
            for p in subdiv:
                pid = p.attrib["id"]
                if pid == "publisher":
                    publisher = etree.SubElement(imprint, "publisher")
                    t = ""
                    for span in p:
                        t += span.text.strip()
                    publisher.text = t.strip()
                elif pid == "publisherAddress":
                    pubPlace = etree.SubElement(imprint, "pubPlace")
                    t = ""
                    for span in p:
                        t += span.text
                    pubPlace.text = t.strip()
    return FRONT, titleStmt


def handle_p(fw, p, tx_line=False):

    def _mk_tx_spans(p):
        notabstart_sr = [0,2,4]#6,8]
        notabstart_du = [1,3,6]#,7,9]
        tabstart_sr = [1,4]#,5,7,9]
        tabstart_du = [3,5]#,6,8,10]
        sr = []
        du = []
        fragments = p.text.split("\t")
        if p.text.startswith("\t"):
            sidx = tabstart_sr
            didx = tabstart_du
        else:
            sidx = notabstart_sr
            didx = notabstart_du
        for ix, f in enumerate(fragments):
            if ix in sidx:
                sr.append(f)
            elif ix in didx:
                du.append(f)
        if p.text.startswith("\t"):
            prev_p = None

            prev = p.getprevious()
            for i in range(5):
                if prev and prev.tag == "p":
                    prev_p = prev
                    break
                elif prev is None:
                    break
                prev = prev.getprevious()
            rm_parent = False
            try:
                sspan = prev_p.find(f"span[@lang=\"srn\"]")
                assert sspan is not None
                rm_parent = True
            except:
                sspan = etree.SubElement(p, "span")
                sspan.attrib["lang"] = "srn"
            try:
                dspan = prev_p.find(f"span[@lang=\"nld\"]")
                assert dspan is not None
                rm_parent = True
            except:
                dspan = etree.SubElement(p, "span")
                dspan.attrib["lang"] = "nld"
            try:
                sspan.text = sspan.text + ' ' + ' '.join(sr)
            except:
                sspan.text = ' '.join(sr)
            try:
                dspan.text = dspan.text + ' ' + ' '.join(du)
            except:
                dspan.text = ' '.join(du)
            if rm_parent:
                p.getparent().remove(p)
        else:
            p.text = None
            sspan = etree.SubElement(p, "span")
            sspan.attrib["lang"] = "srn"
            dspan = etree.SubElement(p, "span")
            dspan.attrib["lang"] = "nld"
            sspan.text = ' '.join(sr)
            dspan.text = ' '.join(du)
        sspan.text = ' '.join([_.strip() for _ in sspan.text.split(' ') if _.strip() not in ['', '.']])
        dspan.text = ' '.join([_.strip() for _ in dspan.text.split(' ') if _.strip() not in ['', '.']])
        return p

    def _spans_to_txt(p):
        t = []
        who = None
        for span in p:
            if span.text is not None:
                if tx_line:
                    t.append(' '.join(span.text.splitlines()))
                else:
                    t.append(' '.join([_.strip() for _ in span.text.splitlines()]))
            elif len(span) == 1 and span.getchildren()[0].tag == "u":
                who = span.getchildren()[0].text
            elif len(span) > 0:
                for child in span:
                    t.append(' '.join([_.strip() for _ in etree.tostring(child).decode().splitlines()]))
        return ' '.join(t), who

    def _default_p(fw, p, tx=False):
        P = etree.SubElement(fw, "p")
        t, who = _spans_to_txt(p)
        P.text = t
        if who:
            P.attrib["who"] = who
        if tx:
            P = _mk_tx_spans(P)
        return fw

    def _find_note_parent(p, ref):
        parent = None
        b = False

        for child in reversed(p):
            if b:
                break
            if child.tag == "p":
                for span in child:
                    if span.tag == "span":
                        if span is not None and span.text is not None and ref in span.text:
                            parent = child
                            b = True
        return parent

    if "class" in p.attrib:
        class_ = p.attrib["class"]
        if class_ == "foot":
            foot = etree.SubElement(fw, 'note')
            foot.attrib["type"] = "pageFooter"
            foot.text, _ = _spans_to_txt(p)
            pb = etree.SubElement(fw, "pb")
        elif class_ == "pnum":
            pnum = etree.SubElement(fw, "note")
            pnum.attrib["type"] = "pageNumber"
            PRE = pnum.getprevious()
            if PRE and not PRE.tag == "pb":
                print(PRE.tag)
                pb = etree.SubElement(fw, "pb")
            pnum.text, _ = _spans_to_txt(p)
        elif class_ == "h2":
            head = etree.SubElement(fw, "head")
            head.attrib["type"] = "h2"
            head.text, _ = _spans_to_txt(p)
        elif class_ == "footNote":
            parent = None
            for span in p:
                try:
                    t = span.text.strip()
                    ref = t[:3]
                    parent = _find_note_parent(fw, ref)
                    if parent:
                        note = etree.SubElement(parent, "note")
                        note.text = ' '.join([_.strip() for _ in t.split(' ') if _.strip() != ''])
                        note.attrib["lang"] = "nld"
                except Exception as e:
                    print("EXCEPT", span, e, [c for c in span.getchildren()])
        else:
            fw = _default_p(fw, p, tx=True)
    else:
        fw = _default_p(fw, p, tx=True)
    return fw


def handle_head_text(head_elem):
    t = []
    for p in head_elem:
        for span in p:
            if span.text is not None:
                t.append(span.text.strip())
            elif len(span) > 0:
                for child in span:
                    t.append(etree.tostring(child).decode())
    return strip_newlines(' '.join(t))


def handle_fw(fw, div):
    for child in div:
        if child.tag == "head":
            head = etree.SubElement(fw, "head")
            head.attrib["type"] = child.attrib["type"]
            head.text = handle_head_text(child)
        elif child.tag == "p":
            fw = handle_p(fw, child)
    return fw


def handle_section(section, div):
    for child in div:
        if child.tag == "head":
            head = etree.SubElement(section, "head")
            head.attrib["type"] = "h1"
            head.text = handle_head_text(child)
        elif child.tag == "div":
            subsection = etree.SubElement(section, "div")
            if div.attrib["id"] == "lessons":
                subsection.attrib["type"] = "lesson"
            for p in child:
                subsection = handle_p(subsection, p, tx_line=True)
        elif child.tag == "p":
            section = handle_p(section, child, tx_line=True)

    return section




def main(args):
    TEI = etree.Element("tei")
    TEI.attrib["xmlns"] = "http://www.tei-c.org/ns/1.0"
    teiHeader = etree.SubElement(TEI, "teiHeader")
    fileDesc = etree.SubElement(teiHeader, "fileDesc")
    titleStmt = etree.SubElement(fileDesc, "titleStmt")
    publicationStmt = etree.SubElement(fileDesc, "PublicationStmt")
    docDate = etree.SubElement(publicationStmt, "date")
    docDate.text = "1765"
    docDate.attrib["when"] = "1765"
    sourceDesc = etree.SubElement(teiHeader, "sourceDesc")
    cmdi = etree.SubElement(sourceDesc, "p")
    cmdi.text = "CMDI Metadata"
    cmdi_ref =  etree.SubElement(cmdi, "ref")
    cmdi_ref.attrib["target"] = "https://hdl.handle.net"

    TEXT = etree.SubElement(TEI, "text")
    FRONT = etree.SubElement(TEXT, "front")
    BODY = etree.SubElement(TEXT, "body")

    root = parse_tei(args.infile, get_ns=False)
    for div in root.findall(".//body/div"):
        _class = div.attrib["class"]
        print(div, _class)
        if _class == "header":
            FRONT, titleStmt = populate_front(div, FRONT, titleStmt)
        elif _class == "foreword":
            fw = etree.SubElement(BODY, "div")
            fw.attrib["type"] = "frontMatter"
            fw = handle_fw(fw, div)
        elif _class == "section":
            section = etree.SubElement(BODY, "div")
            section.attrib["type"] = div.attrib["id"]
            section = handle_section(section, div)
        elif _class == "endMatter":
            pass
        else:
            pass # throw error
    write_tei(TEI, args.outfile)




if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i","--infile", type=str, required=True)
    parser.add_argument("-o", "--outfile", type=str, required=True)
    main(parser.parse_args())
