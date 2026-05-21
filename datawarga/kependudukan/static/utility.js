// This is the js file that loaded on the base template
$('.dateinput').datepicker({format: 'yyyy-mm-dd'});

// indonesian months

const indonesian_months = [
    "",
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember",
];

// Image Lightbox Viewer
$(document).ready(function() {
    $(document).on('click', '.enlargeable-image', function(e) {
        e.preventDefault();
        
        var src = "";
        if ($(this).is('img')) {
            src = $(this).attr('src');
            var parentAnchor = $(this).closest('a');
            if (parentAnchor.length > 0 && parentAnchor.attr('href') && parentAnchor.attr('href') !== '#') {
                src = parentAnchor.attr('href');
            }
        } else if ($(this).is('a')) {
            src = $(this).attr('href');
        }
        
        if (src) {
            $('#lightboxImage').attr('src', src);
            var myModal = new bootstrap.Modal(document.getElementById('imageLightbox'));
            myModal.show();
        }
    });
});