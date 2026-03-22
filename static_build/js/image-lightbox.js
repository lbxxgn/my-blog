document.addEventListener('DOMContentLoaded',function(){const images=document.querySelectorAll('.post-content img');images.forEach(function(img,index){if(!img.complete){return;}
if(img.naturalWidth&&img.naturalWidth<50){return;}
if(!img.src||img.src.startsWith('data:')){return;}
if(img.parentElement&&img.parentElement.tagName==='A'){return;}
const link=document.createElement('a');link.href=img.src;link.setAttribute('data-lightbox','post-images');link.setAttribute('data-title',img.alt||`图片 ${index+1}`);link.setAttribute('data-alt',img.alt||'');link.style.display='inline-block';link.style.position='relative';link.style.lineHeight='0';img.parentNode.insertBefore(link,img);link.appendChild(img);});console.log('Image lightbox initialized for',images.length,'images');});