; Dual-format text compositor and character-oriented five-name editor.
;
; Legacy words (bit 15 clear) use the original 12-pixel Japanese glyph path.
; Marked words contain two 7-bit Latin IDs and render as two independent
; single-character glyphs at six-pixel spacing.

lorom

!TextX = $0208
!TextRowBase = $0202
!TextDrawBase = $0204
!TextWidth = $020A
!TextSurfaceWidth = $020E
!TextSurfaceHeight = $0210
!NamePickerCursor = $0229
!NameCursor = $022B
!EntryMode = $0216

!LatinPickerPage1 = $84F142
!LatinPickerPage2 = $84F232
!LatinSelectionMap1 = $84F322
!LatinSelectionMap2 = $84F3CC

; Replace the compositor prologue with a long dispatch. Legacy calls reproduce
; the displaced PHP/PHB/REP instructions and rejoin at $80:9B30.
org $809B2C
    jml RenderDualFormatWord

; The A-button handler is shared by fresh-name and password entry. Dispatch by
; mode without adding a return address: fresh names use packed Latin editing,
; while password mode reproduces the displaced LDA/CMP and rejoins the original
; one-word insertion path at its BCS.
org $818AD7
    jml EditModeAwareEntryAtCursor

; The page loader is shared with password entry. Fresh name entry uses the
; relocated Latin streams; password mode retains the original streams and
; therefore the original password alphabet.
org $818B5E
    jsl LoadModeAwarePickerPage
    rts

; Character-oriented field cursor.
org $818C38
    jsl PositionModeAwareNameCursor
    rts

; Six-pixel ordinary picker selector. DONE retains its original wider cursor.
org $818BDD
    jsl PositionModeAwarePickerCursor
    rts

; Opening title, New Game, and Options menus share this three-row selector
; table. Move every row up two pixels without affecting other sprite users.
org $818685
    dw $009E,$00AE,$00BE

; Bank 00 all-$FF padding in the pinned original.
org $80EBCF
RenderDualFormatWord:
    php
    rep #$20
    bit #$8000
    bne .latin
    phb
    jml $809B30
.latin:
    rep #$10
    phx
    pha
    and #$007F
    jsr RenderLatinId
    pla
    lsr
    lsr
    lsr
    lsr
    lsr
    lsr
    lsr
    and #$007F
    jsr RenderLatinId
    plx
    plp
    rtl

RenderLatinId:
    cmp #$0000
    beq .blank
    asl
    tax
    lda.l LatinGlyphCodes,x
    pha
    lda !TextWidth
    clc
    adc #$0006
    sta !TextWidth
    pla
    jsl $809B2C
    lda !TextWidth
    sec
    sbc #$0006
    sta !TextWidth
    lda !TextX
    sec
    sbc #$0006
    bra .position
.blank:
    lda !TextX
    clc
    adc #$0006
.position:
    sta !TextX
    lsr
    lsr
    lsr
    asl
    asl
    asl
    asl
    clc
    adc !TextRowBase
    sta !TextDrawBase
    rts

; ID 0 is a generated blank. IDs 1..119 match glyphs.py.
LatinGlyphCodes:
    dw $0272
    dw $0301,$0302,$0303,$0304,$0305,$0306,$0307,$0308
    dw $0311,$0312,$0313,$0314,$0315,$0316,$0317,$0318
    dw $0321,$0322,$0323,$0324,$0325,$0326,$0327,$0328
    dw $0331,$0332,$0333,$0334,$0335,$0336,$0337,$0338
    dw $0341,$0342,$0343,$0344,$0345,$0346,$0347,$0348
    dw $0351,$0352,$0353,$0354,$0355,$0356,$0357,$0358
    dw $0361,$0362,$0363,$0364,$0365,$0366,$0367,$0368
    dw $0371,$0372,$0373,$0374,$0375,$0376,$0377,$0378
    dw $0381,$0382,$0383,$0384,$0385
    dw $0273,$0274,$0275,$0276,$0277
    dw $02D1,$02D2,$02D3,$02D4,$02D5,$02D6,$02D7
    dw $0414,$0415,$0416,$0417
    dw $0420,$0421,$0422,$0423,$0424,$0425,$0426,$0427
    dw $0430,$0431,$0432,$0433,$0434,$0435,$0436,$0437
    dw $0440,$0441,$0442,$0443,$0444,$0445,$0446,$0447
    dw $0450,$0451,$0452,$0453,$0454,$0455,$0456,$0457
    dw $0460,$0461

; Redraw and upload only the edited five-word field. Each displayed name row
; occupies $0100 bytes in the persistent $7E:8000 staging buffer. $EF selects
; both the WRAM source offset and twice the VRAM offset from base $1120; $ED is
; the exclusive transfer end. Explicitly setting all three values avoids
; inheriting the picker's $0100 VRAM base while retaining a one-row transfer.
RedrawLatinNameField:
    php
    rep #$30
    phx
    phy
    lda !NameCursor
    ldx #$0000
    ldy #$0000
.find_field:
    cmp #$000A
    bcc .field_found
    sec
    sbc #$000A
    pha
    txa
    clc
    adc #$000A
    tax
    tya
    clc
    adc #$0100
    tay
    pla
    bra .find_field
.field_found:
    phx
    tya
    sta $EF
    clc
    adc #$0100
    sta $0C
    sta $ED
    lda #$1120
    sta $EB
    tyx
    lda #$0000
.clear_row:
    sta.l $7E8000,x
    inx
    inx
    cpx $0C
    bcc .clear_row
    tya
    sta !TextRowBase
    sta !TextDrawBase
    stz !TextX
    stz $33
    lda #$0008
    sta !TextSurfaceWidth
    lda #$000A
    sta !TextSurfaceHeight
    lda #$0040
    sta !TextWidth
    plx
    ldy #$0005
.render_word:
    lda $0C00,x
    phx
    phy
    jsl $809B2C
    ply
    plx
    inx
    inx
    dey
    bne .render_word
    lda #$0001
    tsb $DC
    jsl $8088D7
    ply
    plx
    plp
    rtl

; Bank 01 all-$FF padding in the pinned original.
org $81DA50
EditModeAwareEntryAtCursor:
    lda !EntryMode
    bne .password
    jml EditFreshNameAtCursor
.password:
    lda !NamePickerCursor
    cmp #$0055
    jml $818ADD

LoadModeAwarePickerPage:
    rep #$30
    ldy #$0000
    lda !EntryMode
    bne .password
    lda $0212
    bit #$0001
    bne .latin_page2
    ldx #$0000
.latin_page1_loop:
    lda.l !LatinPickerPage1,x
    sta $0A00,y
    beq .render
    inx
    inx
    iny
    iny
    bra .latin_page1_loop
.latin_page2:
    ldx #$0000
.latin_page2_loop:
    lda.l !LatinPickerPage2,x
    sta $0A00,y
    beq .render
    inx
    inx
    iny
    iny
    bra .latin_page2_loop
.password:
    lda $0212
    bit #$0001
    bne .password_page2
    ldx #$0000
.password_page1_loop:
    lda.l $84A3E0,x
    sta $0A00,y
    beq .render
    inx
    inx
    iny
    iny
    bra .password_page1_loop
.password_page2:
    ldx #$0000
.password_page2_loop:
    lda.l $84A4D0,x
    sta $0A00,y
    beq .render
    inx
    inx
    iny
    iny
    bra .password_page2_loop
.render:
    lda #$001C
    sta !TextSurfaceWidth
    lda #$000C
    sta !TextSurfaceHeight
    lda #$0100
    sta $EB
    lda #$0A00
    jsl $80997B
    rtl

EditFreshNameAtCursor:
    php
    rep #$30
    lda !NamePickerCursor
    cmp #$0055
    bcs .action
    jsr EnsureNameFieldIsLatin
    lda !NamePickerCursor
    asl
    tax
    lda $0212
    bit #$0001
    bne .page2
    lda.l !LatinSelectionMap1,x
    bra .selected
.page2:
    lda.l !LatinSelectionMap2,x
.selected:
    and #$007F
    sta $04
    lda !NameCursor
    lsr
    php
    asl
    tax
    plp
    bcs .odd
.even:
    lda $0C00,x
    and #$BF80
    ora $04
    sta $0C00,x
    bra .redraw
.odd:
    lda $04
    xba
    lsr
    ora #$8000
    sta $06
    lda $0C00,x
    and #$807F
    ora $06
    sta $0C00,x
.redraw:
    jsl RedrawLatinNameField
    lda !NameCursor
    cmp #$0031
    beq .return_to_editor
    inc !NameCursor
    bra .return_to_editor
.action:
    lda !NameCursor
    cmp #$000A
    bcc .field1
    cmp #$0014
    bcc .field2
    cmp #$001E
    bcc .field3
    cmp #$0028
    bcc .field4
    plp
    rts
.field1:
    lda #$000A
    bra .set
.field2:
    lda #$0014
    bra .set
.field3:
    lda #$001E
    bra .set
.field4:
    lda #$0028
.set:
    sta !NameCursor
.return_to_editor:
    plp
    jml $8189BA

; Localized defaults and edited names already use packed Latin and must be
; preserved. Only a legacy Japanese-format field needs conversion before the
; selected packed byte is overwritten.
EnsureNameFieldIsLatin:
    lda !NameCursor
    ldx #$0000
.field:
    cmp #$000A
    bcc .found
    sec
    sbc #$000A
    txa
    clc
    adc #$000A
    tax
    bra .field
.found:
    lda $0C00,x
    bmi .ready
.clear_field:
    ldy #$0005
    lda #$8000
.clear:
    sta $0C00,x
    inx
    inx
    dey
    bne .clear
.ready:
    rts

PositionModeAwareNameCursor:
    php
    rep #$30
    lda !EntryMode
    bne PositionLegacyNameCursor
    lda !NameCursor
    ldx #$0000
.field:
    cmp #$000A
    bcc .found
    sec
    sbc #$000A
    inx
    bra .field
.found:
    sta $04
    txa
    asl
    asl
    asl
    asl
    clc
    adc #$0096
    sta $48
    lda $04
    asl
    sta $06
    asl
    clc
    adc $06
    clc
    adc #$00B0
    sta $45
    lda $0218
    bit #$0001
    bne .alternate
    lda #$0006
    bra .draw
.alternate:
    lda #$0007
.draw:
    sta $4E
    lda #$3000
    sta $0119
    jsl $8095FB
    jsr NarrowLastSelector
    plp
    rtl

PositionLegacyNameCursor:
    lda !NameCursor
    asl
    tax
    lda.l $818D24,x
    and #$00FF
    sta $45
    lda.l $818D25,x
    and #$00FF
    sta $48
    lda $0218
    bit #$0001
    bne .alternate
    lda #$0006
    bra .draw
.alternate:
    lda #$0007
.draw:
    sta $4E
    lda #$3000
    sta $0119
    jsl $8095FB
    plp
    rtl

PositionModeAwarePickerCursor:
    php
    rep #$30
    lda !EntryMode
    bne PositionLegacyPickerCursor
    lda !NamePickerCursor
    asl
    tax
    lda.l $818C70,x
    and #$00FF
    clc
    adc #$0003
    sta $45
    lda.l $818C71,x
    and #$00FF
    dec
    dec
    sta $48
    lda !NamePickerCursor
    cmp #$0055
    bcs .action
    lda $0218
    bit #$0001
    bne .ordinary_alternate
    lda #$0006
    bra .draw_ordinary
.ordinary_alternate:
    lda #$0007
.draw_ordinary:
    sta $4E
    lda #$3000
    sta $0119
    stz $0115
    jsl $8095FB
    jsr NarrowLastSelector
    plp
    rtl

.action:
    lda $0218
    bit #$0001
    bne .action_alternate
    lda #$000C
    bra .draw_action
.action_alternate:
    lda #$000D
.draw_action:
    sta $4E
    lda #$3000
    sta $0119
    stz $0115
    jsl $8095FB
    plp
    rtl

PositionLegacyPickerCursor:
    lda !NamePickerCursor
    asl
    tax
    lda.l $818C70,x
    and #$00FF
    clc
    adc #$0003
    sta $45
    lda.l $818C71,x
    and #$00FF
    sta $48
    lda !NamePickerCursor
    cmp #$0055
    bcs .action
    lda $0218
    bit #$0001
    bne .ordinary_alternate
    lda #$0006
    bra .draw
.ordinary_alternate:
    lda #$0007
    bra .draw
.action:
    lda $0218
    bit #$0001
    bne .action_alternate
    lda #$000C
    bra .draw
.action_alternate:
    lda #$000D
.draw:
    sta $4E
    lda #$3000
    sta $0119
    stz $0115
    jsl $8095FB
    plp
    rtl

; IDs 6/7 emit the right corners first at X +6. $0115 points immediately
; after the four generated sprites, so move those two corners left relative
; to the selector just drawn without disturbing an earlier staged selector.
NarrowLastSelector:
    rep #$10
    ldx $0115
    sep #$20
    lda.l $7E1FF0,x
    sec
    sbc #$06
    sta.l $7E1FF0,x
    lda.l $7E1FF4,x
    sec
    sbc #$06
    sta.l $7E1FF4,x
    rts