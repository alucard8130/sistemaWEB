$(document).ready(function() {
    // Guarda el número de columnas por mes y total anual
    var mesesCount = window.mesesCount; // accedido desde una variable global
    var colTypes = ['subgrupo', 'tipo', 'presup', 'real', 'var', 'pctvar'];

    function ajustarColspan() {
        // Ajusta colspan de cada th-mes-X
        for (var i = 0; i < mesesCount; i++) {
            var visibleCols = 0;
            for (var j = 2; j < colTypes.length; j++) { // solo las de datos
                if ($('.col-' + colTypes[j] + '.th-mes-' + i + ':visible').length > 0) {
                    visibleCols++;
                }
            }
            var $th = $('.th-mes-' + i).first();
            if (visibleCols === 0) {
                $th.hide();
            } else {
                $th.show().attr('colspan', visibleCols);
            }
        }
        // Ajusta colspan del total anual
        var visibleTotalCols = 0;
        for (var j = 2; j < colTypes.length; j++) {
            if ($('.col-' + colTypes[j] + '.th-total-anual:visible').length > 0) {
                visibleTotalCols++;
            }
        }
        var $thTotal = $('.th-total-anual').first();
        if (visibleTotalCols === 0) {
            $thTotal.hide();
        } else {
            $thTotal.show().attr('colspan', visibleTotalCols);
        }

        // Ajusta colspan del label TOTAL GENERAL
        var visibles = 1; // col-grupo siempre visible
        if ($('.col-subgrupo:visible').length > 0) visibles++;
        if ($('.col-tipo:visible').length > 0) visibles++;
        $('#td-total-general-label').attr('colspan', visibles);
    }

    // Oculta por default las columnas subgrupo y var
    $('.col-var').hide();
    // Marca los botones como activos
    $('.toggle-col[data-col="var"]').addClass('active');

    $('.toggle-col').on('click', function() {
        var col = $(this).data('col');
        var btn = $(this);
        $('.col-' + col).toggle();
        btn.toggleClass('active');
        ajustarColspan();
    });

    ajustarColspan();
});
    