// 点赞功能
async function toggleLike(itemId) {
    const response = await fetch(`/api/items/${itemId}/likes`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    });
    
    const data = await response.json();
    const likeButton = document.getElementById('likeButton');
    const likesCount = document.getElementById('likesCount');
    
    if (data.liked) {
        likeButton.classList.remove('btn-outline-danger');
        likeButton.classList.add('btn-danger');
    } else {
        likeButton.classList.remove('btn-danger');
        likeButton.classList.add('btn-outline-danger');
    }
    
    // 更新点赞数
    const countResponse = await fetch(`/api/items/${itemId}/likes`);
    const countData = await countResponse.json();
    likesCount.textContent = countData.likes_count;
}

// 评论功能
async function submitComment(event) {
    event.preventDefault();
    
    const form = event.target;
    const itemId = form.dataset.itemId;
    const commenterName = document.getElementById('commenterName').value;
    const content = document.getElementById('commentContent').value;
    
    const response = await fetch(`/api/items/${itemId}/comments`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            commenter_name: commenterName,
            content: content
        })
    });
    
    if (response.ok) {
        // 重新加载页面以显示新评论
        window.location.reload();
    }
}

// 图片预览功能
function previewImage(event) {
    const input = event.target;
    const preview = document.getElementById('imagePreview');
    preview.innerHTML = '';
    
    for (const file of input.files) {
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const img = document.createElement('img');
                img.src = e.target.result;
                img.className = 'preview-image';
                preview.appendChild(img);
            }
            reader.readAsDataURL(file);
        }
    }
}

// 管理员功能：删除物品
async function deleteItem(itemId) {
    if (!confirm('Bu eşyayı silmek istediğinizden emin misiniz?')) {
        return;
    }
    
    const response = await fetch(`/api/items/${itemId}`, {
        method: 'DELETE'
    });
    
    if (response.ok) {
        window.location.href = '/admin';
    }
}

// 管理员功能：切换售出状态
async function toggleSoldStatus(itemId) {
    const response = await fetch(`/api/items/${itemId}/toggle_sold`, {
        method: 'POST'
    });
    
    if (response.ok) {
        window.location.reload();
    }
}

// 当页面加载完成时设置事件监听器
document.addEventListener('DOMContentLoaded', function() {
    // 点赞功能
    document.querySelectorAll('.like-button').forEach(button => {
        button.addEventListener('click', async function(e) {
            e.preventDefault();
            const itemId = this.dataset.itemId;
            
            try {
                const response = await fetch(`/api/items/${itemId}/like`, {
                    method: 'POST'
                });
                
                const data = await response.json();
                if (data.success) {
                    // 更新点赞数
                    const likesCount = document.getElementById(`likes-count-${itemId}`);
                    if (likesCount) {
                        likesCount.textContent = data.likes_count;
                    }
                    
                    // 更新按钮状态
                    this.classList.toggle('liked', data.is_liked);
                }
            } catch (error) {
                console.error('Error:', error);
            }
        });
    });

    // 删除功能
    document.querySelectorAll('.delete-item').forEach(button => {
        button.addEventListener('click', async function() {
            if (!confirm('Bu ürünü silmek istediğinizden emin misiniz?')) {
                return;
            }
            
            const itemId = this.dataset.itemId;
            
            try {
                const response = await fetch(`/api/items/${itemId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    // 删除成功后刷新页面
                    window.location.reload();
                } else {
                    alert('Ürün silinirken bir hata oluştu.');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Ürün silinirken bir hata oluştu.');
            }
        });
    });

    // 切换售出状态功能
    document.querySelectorAll('.toggle-sold').forEach(button => {
        button.addEventListener('click', async function() {
            const itemId = this.dataset.itemId;
            const isSold = this.dataset.isSold === 'true';
            
            try {
                const response = await fetch(`/api/items/${itemId}/toggle_sold`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ is_sold: !isSold })
                });
                
                if (response.ok) {
                    // 更新成功后刷新页面
                    window.location.reload();
                } else {
                    alert('Durum güncellenirken bir hata oluştu.');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Durum güncellenirken bir hata oluştu.');
            }
        });
    });

    // 添加商品按钮点击事件
    const addItemButton = document.querySelector('.add-item');
    if (addItemButton) {
        addItemButton.addEventListener('click', function() {
            window.location.href = '/add_item';
        });
    }

    // 编辑按钮点击事件
    document.querySelectorAll('.edit-item').forEach(button => {
        button.addEventListener('click', function() {
            const itemId = this.dataset.itemId;
            window.location.href = `/edit_item/${itemId}`;
        });
    });

    // 图片预览功能
    function previewImage(event) {
        const input = event.target;
        const preview = document.getElementById('imagePreview');
        
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            
            reader.onload = function(e) {
                preview.innerHTML = `<img src="${e.target.result}" class="img-fluid" alt="Preview">`;
            };
            
            reader.readAsDataURL(input.files[0]);
        }
    }

    const imageInput = document.getElementById('images');
    if (imageInput) {
        imageInput.addEventListener('change', previewImage);
    }

    // 设置评论表单监听器
    const commentForm = document.getElementById('commentForm');
    if (commentForm) {
        commentForm.addEventListener('submit', submitComment);
    }
    
    // 设置点赞按钮监听器
    const likeButton = document.getElementById('likeButton');
    if (likeButton) {
        const itemId = likeButton.dataset.itemId;
        likeButton.addEventListener('click', () => toggleLike(itemId));
    }
    
    // 设置图片上传监听器
    const imageInputOld = document.getElementById('images');
    if (imageInputOld) {
        imageInputOld.addEventListener('change', previewImage);
    }
});
