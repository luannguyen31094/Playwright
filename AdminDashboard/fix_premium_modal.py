import codecs, re

premium_modal = """  <!-- Tailwind/Inline Hybrid Modal for Product Details -->
  <div id="productDetailModal"
    class="fixed hidden items-center justify-center transition-opacity duration-300"
    style="z-index: 99999; background-color: rgba(15, 23, 42, 0.6); backdrop-filter: blur(4px); position: fixed; inset: 0px; top: 0px; left: 0px; right: 0px; bottom: 0px; padding: 1rem;"
    onclick="if(event.target === this) closeProductModal()">
    
    <div class="rounded-2xl w-full flex flex-col overflow-hidden transform transition-all scale-100"
         style="max-width: 960px; max-height: 85vh; background-color: #ffffff; box-shadow: 0 20px 40px -10px rgba(0,0,0,0.15); border: 1px solid rgba(226, 232, 240, 0.8); display: flex; flex-direction: column;">
      
      <!-- Modal Header -->
      <div class="px-6 py-4 flex justify-between items-center border-b" 
           style="flex-shrink: 0; background-color: #ffffff; border-bottom: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: center;">
        <div style="display: flex; flex-direction: column;">
          <h3 class="font-bold text-xl inline-flex items-center gap-2" 
              style="color: #1e293b; margin: 0; display: flex; align-items: center; gap: 0.5rem; font-size: 1.125rem;">
            <svg class="w-5 h-5" style="width: 20px; height: 20px; color: #4f46e5;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
            </svg>
            Hồ Sơ Mổ Xẻ Sản Phẩm
          </h3>
          <p class="text-xs mt-1 font-mono tracking-wide opacity-80" 
             style="color: #64748b; margin: 0; padding-left: 1.75rem; margin-top: 2px;">ID: <span id="pModal_id" style="color: #94a3b8;">N/A</span></p>
        </div>
        <button onclick="closeProductModal()" class="rounded-full p-2 transition" 
                style="background-color: transparent; color: #94a3b8; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center;">
          <svg class="w-5 h-5" style="width: 24px; height: 24px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>

      <!-- Modal Body (Scrollable) -->
      <div class="p-6 overflow-y-auto grid grid-cols-1 md:grid-cols-2 gap-8 text-gray-700" 
           style="flex: 1 1 auto; overflow-y: auto; background-color: #f8fafc; color: #334155; padding: 1.5rem; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 2rem;">
        
        <!-- Cột Trái -->
        <div class="space-y-5" style="display: flex; flex-direction: column; gap: 1.25rem;">
          <div class="flex flex-col sm:flex-row gap-5" style="display: flex; gap: 1.25rem; align-items: stretch;">
            <!-- Ảnh thu nhỏ -->
            <div class="relative shrink-0 rounded-xl overflow-hidden shadow-sm border flex items-center justify-center group"
                 style="width: 140px; height: 140px; flex-shrink: 0; background-color: #ffffff; border-color: #e2e8f0; position: relative;">
              <img id="pModal_img" src="img/placeholder.jpg" class="object-cover w-full h-full transition-transform duration-500" alt="Product Thumbnail" style="width: 100%; height: 100%; object-fit: cover;">
              <div class="absolute top-2 right-2 text-white font-black px-2 py-0.5 rounded shadow border uppercase"
                   style="background-color: #ef4444; border-color: #dc2626; position: absolute; top: 0.5rem; right: 0.5rem; font-size: 0.6rem; letter-spacing: 0.05em; border-radius: 0.25rem; z-index: 10;" id="pModal_discount">Sale 0%</div>
            </div>

            <!-- Box Thông tin -->
            <div class="p-4 rounded-xl flex-1 shadow-sm flex items-center"
                 style="background-color: #ffffff; border: 1px solid #e2e8f0; flex: 1; display: flex; align-items: center;">
              <h4 class="font-bold leading-relaxed"
                  style="color: #1e293b; margin: 0; font-size: 0.95rem; line-height: 1.5; font-weight: 600;" id="pModal_title">Tên Sản Phẩm</h4>
            </div>
          </div>

          <!-- Bảng Giá -->
          <div class="grid grid-cols-2 gap-3" style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.75rem;">
            <div class="p-3 rounded-lg shadow-sm border" style="background-color: #ffffff; border-color: #f1f5f9;">
              <div class="uppercase font-bold" style="font-size: 0.65rem; color: #94a3b8; letter-spacing: 0.025em;">Giá Khách Mua</div>
              <div class="font-black mt-1 truncate" style="font-size: 1.125rem; color: #e11d48; font-weight: 800;" id="pModal_price">0 VNĐ</div>
            </div>
            <div class="p-3 rounded-lg shadow-sm border" style="background-color: #ffffff; border-color: #f1f5f9;">
              <div class="uppercase font-bold" style="font-size: 0.65rem; color: #94a3b8; letter-spacing: 0.025em;">Cò (Hoa Hồng)</div>
              <div class="font-black mt-1 truncate" style="font-size: 1.125rem; color: #059669; font-weight: 800;" id="pModal_commission">0 VNĐ</div>
            </div>
            <div class="p-3 rounded-lg shadow-sm border" style="background-color: #ffffff; border-color: #f1f5f9;">
              <div class="uppercase font-bold" style="font-size: 0.65rem; color: #94a3b8; letter-spacing: 0.025em;">Đã Chốt</div>
              <div class="font-black mt-1 truncate" style="font-size: 1.125rem; color: #334155; font-weight: 800;" id="pModal_sold">0</div>
            </div>
            <div class="p-3 rounded-lg shadow-sm border" style="background-color: #ffffff; border-color: #f1f5f9;">
              <div class="uppercase font-bold" style="font-size: 0.65rem; color: #94a3b8; letter-spacing: 0.025em;">Rating</div>
              <div class="font-black mt-1 truncate" style="font-size: 1.125rem; color: #d97706; font-weight: 800;" id="pModal_rating">0</div>
            </div>
          </div>
        </div>

        <!-- Cột Phải -->
        <div class="flex flex-col h-full" style="display: flex; flex-direction: column; gap: 1.25rem; height: 100%;">
          <div class="rounded-xl overflow-hidden shadow-sm border flex flex-col flex-1" style="background-color: #ffffff; border-color: #e2e8f0; flex: 1; display: flex;">
            
            <div class="px-4 py-3 border-b font-bold flex items-center gap-2 uppercase tracking-wider"
                 style="background-color: #ffffff; border-bottom: 1px solid #f1f5f9; color: #64748b; font-size: 0.7rem; display: flex; align-items: center; gap: 0.5rem; letter-spacing: 0.05em;">
              <svg class="w-4 h-4" style="width: 16px; height: 16px; color: #8b5cf6;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
              </svg>
              AI Phân Tích Thông Minh
            </div>
            
            <div class="p-4 flex flex-col flex-1" style="display: flex; flex-direction: column; gap: 1.25rem; flex: 1;">
              <div class="flex items-center justify-around rounded-lg p-3 border"
                   style="background-color: #f8fafc; border-color: #f1f5f9; display: flex; align-items: center;">
                <div class="text-center" style="flex: 1; text-align: center;">
                  <div class="font-bold uppercase tracking-widest" style="font-size: 0.65rem; color: #94a3b8; margin-bottom: 0.25rem;">Điểm AI Máy Tính</div>
                  <div class="font-black" style="font-size: 2.5rem; color: #f43f5e; line-height: 1; font-weight: 900;" id="pModal_ai_score">0</div>
                </div>
                <div style="width: 1px; height: 50px; background-color: #e2e8f0;"></div>
                <div class="text-center" style="flex: 1; text-align: center;">
                  <div class="font-bold uppercase tracking-widest" style="font-size: 0.65rem; color: #94a3b8; margin-bottom: 0.25rem;">Lực Chiến Cơ Bản</div>
                  <div class="font-black" style="font-size: 2.5rem; color: #3b82f6; line-height: 1; font-weight: 900;" id="pModal_total_score">0</div>
                </div>
              </div>

              <div class="flex flex-col flex-1" style="display: flex; flex-direction: column; flex: 1;">
                <label class="font-bold uppercase tracking-widest flex items-center gap-1" style="font-size: 0.65rem; color: #64748b; margin-bottom: 0.5rem;">
                  Tóm Tắt Khách Quan (Logs)
                </label>
                <textarea id="pModal_ai_note" class="w-full rounded-lg p-4 outline-none resize-none shadow-sm border"
                  style="background-color: #f8fafc; border: 1px solid #e2e8f0; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 0.8rem; color: #475569; line-height: 1.6; flex: 1; width: 100%; border-radius: 0.5rem; box-sizing: border-box; min-height: 120px;"
                  readonly></textarea>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Modal Footer -->
      <div class="px-6 py-3 flex justify-end border-t" 
           style="flex-shrink: 0; background-color: #ffffff; border-top: 1px solid #f1f5f9; display: flex; justify-content: flex-end; align-items: center;">
          <button type="button" onclick="closeProductModal()" class="px-6 py-2 rounded-lg font-medium transition shadow-sm"
                  style="background-color: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; cursor: pointer; font-size: 0.85rem; font-weight: 600;">Đóng Lại</button>
      </div>
    </div>
  </div>\n"""

with codecs.open('index.html', 'r', 'utf-8') as f:
    text = f.read()

text = re.sub(r'  <!-- Tailwind/Inline Hybrid Modal for Product Details -->[\s\S]*?(?=<!-- DUAL-PERSONA GLOBAL MODALS -->)', premium_modal, text)

with codecs.open('index.html', 'w', 'utf-8') as f:
    f.write(text)
print("Premium scrollable modal injected!")
