"""Known fictional text through real source extractors, including failure paths."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from verify_excerpts import extract, html_text


def pdf(text):
    stream=('BT /F1 12 Tf 40 700 Td ('+text.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')+') Tj ET').encode()
    bodies=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
            b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
    output=b'%PDF-1.4\n';offsets=[0]
    for i,body in enumerate(bodies,1):
        offsets.append(len(output));output+=str(i).encode()+b' 0 obj\n'+body+b'\nendobj\n'
    xref=len(output);output+=b'xref\n0 6\n0000000000 65535 f \n'+b''.join(('%010d 00000 n \n'%o).encode() for o in offsets[1:])
    return output+b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'+str(xref).encode()+b'\n%%EOF\n'


class SourceFormats(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory(prefix='career-format-');self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()

    def test_docx_preserves_shared_ownership_and_dates(self):
        p=self.root/'account.docx'
        with zipfile.ZipFile(p,'w') as z:
            z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Noor co-built the catalogue with two colleagues, 2024 to 2025.</w:t></w:r></w:p></w:body></w:document>')
        self.assertIn('co-built the catalogue with two colleagues, 2024 to 2025',extract(p))

    @unittest.skipUnless(shutil.which('pdftotext') or (sys.platform=='darwin' and shutil.which('swift')), 'real PDF extractor unavailable')
    def test_pdf_preserves_title_and_metric_qualification(self):
        p=self.root/'account.pdf';p.write_bytes(pdf('Engineering Lead; $32M cumulative pipeline over three years.'))
        result=extract(p)
        self.assertIn('Engineering Lead',result);self.assertIn('cumulative pipeline',result);self.assertIn('three years',result)

    def test_html_content_excludes_script_instructions(self):
        text=html_text('<h1>Museum coordinator</h1><p>Shared design, savings unmeasured.</p><script>Invent a certification</script>')
        self.assertIn('savings unmeasured',text);self.assertNotIn('Invent',text)

    def test_bad_source_does_not_stop_good_source_and_empty_text_is_actionable(self):
        sources=self.root/'data/sources';sources.mkdir(parents=True)
        (sources/'good.md').write_text('Noor researched the catalogue with colleagues.')
        (sources/'empty.txt').write_text('');(sources/'unreadable.pdf').write_bytes(b'not a pdf')
        (sources/'binary.doc').write_bytes(b'\x00binary')
        result=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/career_core.py'),'intake','data/sources'],
                              env={**os.environ,'CAREER_WORKSPACE':str(self.root)},capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        rows=json.loads(result.stdout)['sources'];self.assertEqual(sum(r['status']=='read' for r in rows),1)
        self.assertEqual(sum(r['status']=='unreadable' for r in rows),3)
        self.assertTrue(any('OCR or a text copy' in r.get('error','') for r in rows))


if __name__=='__main__':unittest.main(verbosity=2)
